import os

# Define the modules
modules = [
    'ophthalmic',
    'ent',
    'oncology',
    'scbu',
    'anc',
    'labor',
    'icu',
    'family_planning',
    'gynae_emergency'
]

# Define the base path
base_path = os.getcwd()

# Generate templates for each module
for module in modules:
    templates_path = os.path.join(base_path, module, 'templates', module)
    
    # Create list template
    with open(os.path.join(templates_path, f'{module}_records_list.html'), 'w') as f:
        f.write(f'''{{% extends 'base.html' %}}
{{% load static %}}

{{% block title %}}{module.capitalize()} Records{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="d-sm-flex align-items-center justify-content-between mb-4">
        <h1 class="h3 mb-0 text-gray-800">{module.capitalize()} Records</h1>
        <a href="{{% url '{module}:create_{module}_record' %}}" class="btn btn-primary">
            <i class="fas fa-plus"></i> Add New Record
        </a>
    </div>

    <!-- Search Form -->
    <div class="card shadow mb-4">
        <div class="card-body">
            <form method="GET" class="form-inline">
                <div class="form-group mr-2">
                    <input type="text" class="form-control" name="search" placeholder="Search patients or diagnosis..." value="{{{{ search_query }}}}">
                </div>
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-search"></i> Search
                </button>
                {{% if search_query %}}
                <a href="{{% url '{module}:{module}_records_list' %}}" class="btn btn-secondary ml-2">
                    <i class="fas fa-times"></i> Clear
                </a>
                {{% endif %}}
            </form>
        </div>
    </div>

    <!-- Records List -->
    <div class="card shadow mb-4">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-bordered table-striped">
                    <thead>
                        <tr>
                            <th>Patient</th>
                            <th>Visit Date</th>
                            <th>Doctor</th>
                            <th>Diagnosis</th>
                            <th>Follow-up</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{% for record in page_obj %}}
                        <tr>
                            <td>{{{{ record.patient.get_full_name }}}}</td>
                            <td>{{{{ record.visit_date|date:"M d, Y" }}}}</td>
                            <td>{{{{ record.doctor.get_full_name|default:"Not specified" }}}}</td>
                            <td>{{{{ record.diagnosis|truncatewords:10 }}}}</td>
                            <td>
                                {{% if record.follow_up_required %}}
                                <span class="badge badge-warning">Required</span>
                                {{% if record.follow_up_date %}}
                                <br><small>{{{{ record.follow_up_date|date:"M d, Y" }}}}</small>
                                {{% endif %}}
                                {{% else %}}
                                <span class="badge badge-secondary">Not required</span>
                                {{% endif %}}
                            </td>
                            <td>
                                <a href="{{% url '{module}:{module}_record_detail' record.id %}}" class="btn btn-info btn-sm">
                                    <i class="fas fa-eye"></i> View
                                </a>
                                <a href="{{% url '{module}:edit_{module}_record' record.id %}}" class="btn btn-warning btn-sm">
                                    <i class="fas fa-edit"></i> Edit
                                </a>
                            </td>
                        </tr>
                        {{% empty %}}
                        <tr>
                            <td colspan="6" class="text-center">No {module} records found.</td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>
            
            <!-- Pagination -->
            {{% if page_obj.has_other_pages %}}
            <nav aria-label="Page navigation">
                <ul class="pagination justify-content-center">
                    {{% if page_obj.has_previous %}}
                    <li class="page-item">
                        <a class="page-link" href="?page=1{{% if search_query %}}&search={{{{ search_query }}}}{{% endif %}}">First</a>
                    </li>
                    <li class="page-item">
                        <a class="page-link" href="?page={{{{ page_obj.previous_page_number }}}}{{% if search_query %}}&search={{{{ search_query }}}}{{% endif %}}">Previous</a>
                    </li>
                    {{% endif %}}
                    
                    <li class="page-item active">
                        <span class="page-link">{{{{ page_obj.number }}}} of {{{{ page_obj.paginator.num_pages }}}}</span>
                    </li>
                    
                    {{% if page_obj.has_next %}}
                    <li class="page-item">
                        <a class="page-link" href="?page={{{{ page_obj.next_page_number }}}}{{% if search_query %}}&search={{{{ search_query }}}}{{% endif %}}">Next</a>
                    </li>
                    <li class="page-item">
                        <a class="page-link" href="?page={{{{ page_obj.paginator.num_pages }}}}{{% if search_query %}}&search={{{{ search_query }}}}{{% endif %}}">Last</a>
                    </li>
                    {{% endif %}}
                </ul>
            </nav>
            {{% endif %}}
        </div>
    </div>
</div>
{{% endblock %}}''')

    # Create form template
    with open(os.path.join(templates_path, f'{module}_record_form.html'), 'w') as f:
        f.write(f'''{{% extends 'base.html' %}}
{{% load static %}}
{{% load widget_tweaks %}}

{{% block title %}}{{{{ title }}}}{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="d-sm-flex align-items-center justify-content-between mb-4">
        <h1 class="h3 mb-0 text-gray-800">{{{{ title }}}}</h1>
    </div>

    <div class="card shadow mb-4">
        <div class="card-body">
            <form method="POST">
                {{% csrf_token %}}
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="{{{{ form.patient.id_for_label }}}}">Patient *</label>
                            {{{{ form.patient|add_class:"form-control" }}}}
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="{{{{ form.doctor.id_for_label }}}}">Doctor</label>
                            {{{{ form.doctor|add_class:"form-control" }}}}
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="{{{{ form.visit_date.id_for_label }}}}">Visit Date *</label>
                            {{{{ form.visit_date|add_class:"form-control" }}}}
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="{{{{ form.chief_complaint.id_for_label }}}}">Chief Complaint</label>
                    {{{{ form.chief_complaint|add_class:"form-control" }}}}
                </div>
                
                <div class="form-group">
                    <label for="{{{{ form.history_of_present_illness.id_for_label }}}}">History of Present Illness</label>
                    {{{{ form.history_of_present_illness|add_class:"form-control" }}}}
                </div>
                
                <div class="form-group">
                    <label for="{{{{ form.diagnosis.id_for_label }}}}">Diagnosis</label>
                    {{{{ form.diagnosis|add_class:"form-control" }}}}
                </div>
                
                <div class="form-group">
                    <label for="{{{{ form.treatment_plan.id_for_label }}}}">Treatment Plan</label>
                    {{{{ form.treatment_plan|add_class:"form-control" }}}}
                </div>
                
                <div class="row">
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="{{{{ form.follow_up_required.id_for_label }}}}">Follow-up Required</label>
                            {{{{ form.follow_up_required|add_class:"form-control" }}}}
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="form-group">
                            <label for="{{{{ form.follow_up_date.id_for_label }}}}">Follow-up Date</label>
                            {{{{ form.follow_up_date|add_class:"form-control" }}}}
                        </div>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="{{{{ form.notes.id_for_label }}}}">Notes</label>
                    {{{{ form.notes|add_class:"form-control" }}}}
                </div>
                
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-save"></i> Save Record
                </button>
                <a href="{{% url '{module}:{module}_records_list' %}}" class="btn btn-secondary">
                    <i class="fas fa-times"></i> Cancel
                </a>
            </form>
        </div>
    </div>
</div>
{{% endblock %}}''')

    # Create detail template
    with open(os.path.join(templates_path, f'{module}_record_detail.html'), 'w') as f:
        f.write(f'''{{% extends 'base.html' %}}
{{% load static %}}

{{% block title %}}{module.capitalize()} Record Details{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="d-sm-flex align-items-center justify-content-between mb-4">
        <h1 class="h3 mb-0 text-gray-800">{module.capitalize()} Record Details</h1>
        <div>
            <a href="{{% url '{module}:edit_{module}_record' record.id %}}" class="btn btn-warning">
                <i class="fas fa-edit"></i> Edit Record
            </a>
            <a href="{{% url '{module}:{module}_records_list' %}}" class="btn btn-secondary">
                <i class="fas fa-arrow-left"></i> Back to List
            </a>
        </div>
    </div>

    <!-- Patient Information -->
    <div class="card shadow mb-4">
        <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Patient Information</h6>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Name:</strong> {{{{ record.patient.get_full_name }}}}</p>
                    <p><strong>Patient ID:</strong> {{{{ record.patient.patient_id }}}}</p>
                    <p><strong>Age:</strong> {{{{ record.patient.age }}}} years</p>
                    <p><strong>Gender:</strong> {{{{ record.patient.get_gender_display }}}}</p>
                </div>
                <div class="col-md-6">
                    <p><strong>Visit Date:</strong> {{{{ record.visit_date|date:"M d, Y H:i" }}}}</p>
                    <p><strong>Doctor:</strong> {{{{ record.doctor.get_full_name|default:"Not specified" }}}}</p>
                    <p><strong>Follow-up Required:</strong> 
                        {{% if record.follow_up_required %}}
                            <span class="badge badge-warning">Yes</span>
                            {{% if record.follow_up_date %}}
                                <br><strong>Follow-up Date:</strong> {{{{ record.follow_up_date|date:"M d, Y" }}}}
                            {{% endif %}}
                        {{% else %}}
                            <span class="badge badge-secondary">No</span>
                        {{% endif %}}
                    </p>
                </div>
            </div>
        </div>
    </div>

    <!-- Chief Complaint -->
    {{% if record.chief_complaint %}}
    <div class="card shadow mb-4">
        <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Chief Complaint</h6>
        </div>
        <div class="card-body">
            <p>{{{{ record.chief_complaint|linebreaks }}}}</p>
        </div>
    </div>
    {{% endif %}}

    <!-- History of Present Illness -->
    {{% if record.history_of_present_illness %}}
    <div class="card shadow mb-4">
        <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">History of Present Illness</h6>
        </div>
        <div class="card-body">
            <p>{{{{ record.history_of_present_illness|linebreaks }}}}</p>
        </div>
    </div>
    {{% endif %}}

    <!-- Diagnosis -->
    {{% if record.diagnosis %}}
    <div class="card shadow mb-4">
        <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Diagnosis</h6>
        </div>
        <div class="card-body">
            <p>{{{{ record.diagnosis|linebreaks }}}}</p>
        </div>
    </div>
    {{% endif %}}

    <!-- Treatment Plan -->
    {{% if record.treatment_plan %}}
    <div class="card shadow mb-4">
        <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Treatment Plan</h6>
        </div>
        <div class="card-body">
            <p>{{{{ record.treatment_plan|linebreaks }}}}</p>
        </div>
    </div>
    {{% endif %}}

    <!-- Notes -->
    {{% if record.notes %}}
    <div class="card shadow mb-4">
        <div class="card-header py-3">
            <h6 class="m-0 font-weight-bold text-primary">Notes</h6>
        </div>
        <div class="card-body">
            <p>{{{{ record.notes|linebreaks }}}}</p>
        </div>
    </div>
    {{% endif %}}
</div>
{{% endblock %}}''')

    # Create confirm delete template
    with open(os.path.join(templates_path, f'{module}_record_confirm_delete.html'), 'w') as f:
        f.write(f'''{{% extends 'base.html' %}}
{{% load static %}}

{{% block title %}}Delete {module.capitalize()} Record{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="d-sm-flex align-items-center justify-content-between mb-4">
        <h1 class="h3 mb-0 text-gray-800">Delete {module.capitalize()} Record</h1>
    </div>

    <div class="card shadow mb-4">
        <div class="card-body">
            <div class="alert alert-warning">
                <h4 class="alert-heading">Warning!</h4>
                <p>Are you sure you want to delete the {module} record for <strong>{{{{ record.patient.get_full_name }}}}</strong> dated {{{{ record.visit_date|date:"M d, Y" }}}}?</p>
                <p>This action cannot be undone.</p>
            </div>
            
            <form method="POST">
                {{% csrf_token %}}
                <button type="submit" class="btn btn-danger">
                    <i class="fas fa-trash"></i> Yes, Delete
                </button>
                <a href="{{% url '{module}:{module}_record_detail' record.id %}}" class="btn btn-secondary">
                    <i class="fas fa-times"></i> Cancel
                </a>
            </form>
        </div>
    </div>
</div>
{{% endblock %}}''')

print("Templates created successfully for all modules!")