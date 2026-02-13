from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from theatre.models import SurgeryType, SurgicalEquipment, SurgeryTypeEquipment
from pharmacy.models import MedicalPack, MedicalPackItem
from .views import theatre_access_required


@login_required
@theatre_access_required
def manage_surgery_type_equipment(request, surgery_type_id):
    """
    View to manage equipment requirements for a specific surgery type.
    Shows current equipment and allows assignment from medical packs.
    """
    surgery_type = get_object_or_404(SurgeryType, id=surgery_type_id)

    # Get current equipment assignments
    current_equipment = SurgeryTypeEquipment.objects.filter(
        surgery_type=surgery_type
    ).select_related("equipment")

    # Get all available equipment
    available_equipment = SurgicalEquipment.objects.filter(is_available=True).order_by(
        "name"
    )

    # Find matching medical packs for this surgery type
    surgery_type_mapping = {
        "Appendectomy": "appendectomy",
        "Cholecystectomy": "cholecystectomy",
        "Hernia Repair": "hernia_repair",
        "Cesarean Section": "cesarean_section",
        "Tonsillectomy": "tonsillectomy",
    }

    pack_surgery_type = surgery_type_mapping.get(surgery_type.name)
    suggested_equipment = []

    if pack_surgery_type:
        # Get equipment from medical packs
        pack_equipment = MedicalPackItem.objects.filter(
            pack__surgery_type=pack_surgery_type,
            pack__pack_type="surgery",
            item_type="equipment",
        ).select_related("medication", "pack")

        for item in pack_equipment:
            suggested_equipment.append(
                {
                    "medication": item.medication,
                    "quantity": item.quantity,
                    "is_optional": item.is_optional,
                    "usage_instructions": item.usage_instructions,
                    "pack_name": item.pack.name,
                }
            )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_equipment":
            equipment_id = request.POST.get("equipment_id")
            quantity = request.POST.get("quantity", 1)
            is_mandatory = request.POST.get("is_mandatory") == "on"
            notes = request.POST.get("notes", "")

            try:
                equipment = SurgicalEquipment.objects.get(id=equipment_id)
                SurgeryTypeEquipment.objects.create(
                    surgery_type=surgery_type,
                    equipment=equipment,
                    quantity_required=quantity,
                    is_mandatory=is_mandatory,
                    notes=notes,
                )
                messages.success(
                    request, f"Added {equipment.name} to required equipment."
                )
            except SurgicalEquipment.DoesNotExist:
                messages.error(request, "Equipment not found.")
            except Exception as e:
                messages.error(request, f"Error adding equipment: {str(e)}")

        elif action == "remove_equipment":
            equipment_id = request.POST.get("equipment_id")
            try:
                SurgeryTypeEquipment.objects.get(
                    surgery_type=surgery_type, equipment_id=equipment_id
                ).delete()
                messages.success(request, "Equipment removed from requirements.")
            except SurgeryTypeEquipment.DoesNotExist:
                messages.error(request, "Equipment assignment not found.")

        elif action == "auto_assign_from_packs":
            # Automatically assign all equipment from matching packs
            assigned_count = 0

            if pack_surgery_type:
                with transaction.atomic():
                    for item in suggested_equipment:
                        # Get or create SurgicalEquipment
                        equipment, created = SurgicalEquipment.objects.get_or_create(
                            name=item["medication"].name,
                            defaults={
                                "equipment_type": "instrument",
                                "description": item["medication"].description
                                or f"Equipment for {surgery_type.name}",
                                "quantity_available": 10,
                                "is_available": True,
                            },
                        )

                        # Create or update SurgeryTypeEquipment
                        surgery_type_equip, created = (
                            SurgeryTypeEquipment.objects.get_or_create(
                                surgery_type=surgery_type,
                                equipment=equipment,
                                defaults={
                                    "quantity_required": item["quantity"],
                                    "is_mandatory": not item["is_optional"],
                                    "notes": item["usage_instructions"]
                                    or f"From {item['pack_name']}",
                                },
                            )
                        )

                        if created:
                            assigned_count += 1

                if assigned_count > 0:
                    messages.success(
                        request,
                        f"Successfully assigned {assigned_count} equipment items from medical packs.",
                    )
                else:
                    messages.info(request, "No new equipment assignments were made.")
            else:
                messages.warning(
                    request, "No matching medical packs found for this surgery type."
                )

        return redirect(
            "theatre:manage_surgery_type_equipment", surgery_type_id=surgery_type_id
        )

    # Calculate statistics
    mandatory_count = sum(1 for e in current_equipment if e.is_mandatory)
    available_count = sum(
        1
        for e in current_equipment
        if e.equipment.is_available
        and e.equipment.quantity_available >= e.quantity_required
    )

    context = {
        "surgery_type": surgery_type,
        "current_equipment": current_equipment,
        "available_equipment": available_equipment,
        "suggested_equipment": suggested_equipment,
        "has_matching_packs": pack_surgery_type is not None,
        "mandatory_count": mandatory_count,
        "available_count": available_count,
    }

    return render(request, "theatre/manage_surgery_type_equipment.html", context)
