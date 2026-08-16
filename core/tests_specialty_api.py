"""The eighteen specialty modules through one generic API.

What matters here is that the *machinery* holds for every module — the schema
is derived from the model, so a label can never go stale, and a module added to
`SPECIALTY_MODULES` is reachable without a line of new view code.
"""
from django.test import Client, TestCase, override_settings

from accounts.models import CustomUser, Role
from core.specialty_api import SPECIALTY_MODULES, model_for, note_model_for
from patients.models import Patient


@override_settings(STRICT_ACCESS_CONTROL=True)
class SpecialtyApiTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_superuser(
            phone_number="08017000001", username="specialist", password="pw12345",
        )
        self.auth = self.token_for("08017000001", "pw12345")
        self.patient = Patient.objects.create(
            first_name="Chidi", last_name="Anyanwu", date_of_birth="1985-04-04",
            gender="M", address="8 Clinic Road", city="Aba", state="Abia",
        )

    # --- helpers ----------------------------------------------------------

    def token_for(self, phone, password):
        response = Client().post(
            "/api/accounts/login/",
            {"phone_number": phone, "password": password},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content
        return {"HTTP_AUTHORIZATION": f"Token {response.json()['token']}"}

    def get(self, path, auth=None):
        return self.client.get(path, **(auth or self.auth))

    def post(self, path, payload=None, auth=None):
        return self.client.post(
            path, payload or {}, content_type="application/json",
            **(auth or self.auth),
        )

    # --- the machinery ----------------------------------------------------

    def test_every_module_is_listed_and_resolvable(self):
        rows = self.get("/api/specialty/modules/").json()
        assert len(rows) == len(SPECIALTY_MODULES)
        for row in rows:
            assert model_for(row["kind"]) is not None, row["kind"]

    def test_every_module_serves_a_usable_schema(self):
        """The schema is what one screen renders eighteen modules from."""
        for kind in SPECIALTY_MODULES:
            body = self.get(f"/api/specialty/{kind}/schema/").json()
            assert body["fields"], f"{kind} has no fields"
            names = {field["name"] for field in body["fields"]}
            assert "patient" not in names, f"{kind} should render patient itself"
            for field in body["fields"]:
                assert field["type"] in {
                    "text", "string", "number", "boolean", "date", "datetime",
                    "choice", "reference",
                }, (kind, field)

    def test_schema_labels_come_from_the_model(self):
        fields = {
            field["name"]: field
            for field in self.get("/api/specialty/ent/schema/").json()["fields"]
        }
        assert fields["nose_examination"]["label"] == "Nose examination"
        assert fields["nose_examination"]["type"] == "text"
        assert fields["follow_up_required"]["type"] == "boolean"
        assert fields["visit_date"]["type"] == "datetime"

    def test_unknown_module_is_a_404(self):
        response = self.get("/api/specialty/phrenology/schema/")
        assert response.status_code == 404
        assert "Unknown specialty module" in response.json()["error"]

    # --- records ----------------------------------------------------------

    def test_record_written_and_read_back(self):
        response = self.post("/api/specialty/ent/records/", {
            "patient": self.patient.id,
            "chief_complaint": "Left ear pain for three days",
            "nose_examination": "Clear",
            "diagnosis": "Otitis externa",
            "treatment_plan": "Topical antibiotic drops",
            "follow_up_required": True,
        })
        assert response.status_code == 201, response.content
        body = response.json()
        assert body["patient_name"] == self.patient.get_full_name()
        assert body["diagnosis"] == "Otitis externa"

        rows = self.get(
            f"/api/specialty/ent/records/?patient={self.patient.id}"
        ).json()
        assert rows["count"] == 1

    def test_record_is_patchable(self):
        record_id = self.post("/api/specialty/ent/records/", {
            "patient": self.patient.id, "diagnosis": "Otitis externa",
        }).json()["id"]

        response = self.client.patch(
            f"/api/specialty/ent/records/{record_id}/",
            {"treatment_plan": "Add analgesia"},
            content_type="application/json",
            **self.auth,
        )
        assert response.status_code == 200, response.content
        assert response.json()["treatment_plan"] == "Add analgesia"

    def test_records_are_kept_apart_by_module(self):
        self.post("/api/specialty/ent/records/", {
            "patient": self.patient.id, "diagnosis": "Otitis externa",
        })
        assert self.get("/api/specialty/ent/records/").json()["count"] == 1
        assert self.get("/api/specialty/oncology/records/").json()["count"] == 0

    def test_search_finds_a_patient_across_a_module(self):
        self.post("/api/specialty/ent/records/", {
            "patient": self.patient.id, "diagnosis": "Otitis externa",
        })
        rows = self.get("/api/specialty/ent/records/?search=Anyanwu").json()
        assert rows["count"] == 1
        rows = self.get("/api/specialty/ent/records/?search=Nobody").json()
        assert rows["count"] == 0

    # --- clinical notes ---------------------------------------------------

    def test_clerking_note_written_against_a_record(self):
        record_id = self.post("/api/specialty/ent/records/", {
            "patient": self.patient.id, "diagnosis": "Otitis externa",
        }).json()["id"]

        response = self.post(
            f"/api/specialty/ent/records/{record_id}/clinical-notes/",
            {
                "presenting_complaint": "Ear pain",
                "examination_findings": "Tender tragus",
            },
        )
        assert response.status_code == 201, response.content
        assert response.json()["presenting_complaint"] == "Ear pain"
        assert response.json()["created_by_name"]

        rows = self.get(
            f"/api/specialty/ent/records/{record_id}/clinical-notes/"
        ).json()
        assert len(rows) == 1

    def test_empty_clerking_note_refused(self):
        record_id = self.post("/api/specialty/ent/records/", {
            "patient": self.patient.id, "diagnosis": "Otitis externa",
        }).json()["id"]

        response = self.post(
            f"/api/specialty/ent/records/{record_id}/clinical-notes/",
            {"presenting_complaint": "   "},
        )
        assert response.status_code == 400
        assert "at least one section" in response.json()["error"]

    def test_no_module_keeps_its_authorization_code_as_free_text(self):
        """A code the desk office issued must be a link, not a typed string.

        oncology and anc used to store it as a CharField, so nothing checked it
        against nhia.AuthorizationCode.
        """
        from django.db import models as django_models

        for kind in SPECIALTY_MODULES:
            model = model_for(kind)
            field = next(
                (f for f in model._meta.fields if f.name == 'authorization_code'),
                None,
            )
            if field is None:
                continue
            assert isinstance(field, django_models.ForeignKey), (
                f"{kind}.authorization_code is {type(field).__name__}, not a link"
            )
            assert field.related_model.__name__ == 'AuthorizationCode', kind

    def test_every_module_with_notes_resolves_its_note_model(self):
        for kind in SPECIALTY_MODULES:
            note_model, field = note_model_for(kind)
            if note_model is not None:
                assert field, kind

    # --- access -----------------------------------------------------------

    def test_specialty_records_are_restricted_to_clinical_staff(self):
        clerk = CustomUser.objects.create_user(
            phone_number="08017000002", username="deskclerk", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="receptionist")
        clerk.roles.add(role)
        auth = self.token_for("08017000002", "pw12345")

        response = self.get("/api/specialty/ent/records/", auth=auth)
        assert response.status_code == 403, response.content

    def test_clinical_staff_without_add_permission_cannot_write(self):
        nurse = CustomUser.objects.create_user(
            phone_number="08017000003", username="wardnurse2", password="pw12345",
        )
        role, _ = Role.objects.get_or_create(name="nurse")
        nurse.roles.add(role)
        auth = self.token_for("08017000003", "pw12345")

        assert self.get("/api/specialty/ent/records/", auth=auth).status_code == 200
        response = self.post("/api/specialty/ent/records/", {
            "patient": self.patient.id, "diagnosis": "Otitis externa",
        }, auth=auth)
        assert response.status_code == 403, response.content
