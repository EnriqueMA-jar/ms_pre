from flask import session, redirect, url_for, render_template

@app.route('/set_workflow/<int:workflow_id>')
def set_workflow(workflow_id):
    # Puedes mapear los IDs a nombres si lo deseas
    workflows = {1: "Untargeted Metabolomics Pre-Processing", 2: "Identification by Accurate Mass"}
    session['workflow'] = workflows.get(workflow_id, "Unknown Workflow")
    session['workflow_status'] = 'active'
    return redirect(url_for('index'))

@app.route('/end_workflow')
def end_workflow():
    session.pop('workflow', None)
    session['workflow_status'] = 'inactive'
    return redirect(url_for('index'))

@app.route('/index')
def index():
    return render_template(
        'index.html',
        workflow_status=session.get('workflow_status', 'inactive'),
        current_workflow=session.get('workflow', '')
    )