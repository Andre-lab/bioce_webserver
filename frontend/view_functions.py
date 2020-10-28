"""
These are essential helper functions for the upload, analysis and profile views.
"""

import datetime
import json
import os

from flask import request
from flask_security import current_user
from werkzeug.utils import secure_filename

from . import app, db, models

# -----------------------------------------------------------------------------
# UPLOAD - HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def get_form(form, files):
    """
    Merges files and form values of request, because flask separates them.
    """
    form_dict = {}
    for k, v in request.values.items():
        form_dict[k] = v
    for k, v in request.files.items():
        form_dict[k] = v
    return form_dict


def save_study(form, files):
    """
    Creates study folder, saves uploaded files, checks their formatting
    """
    # setup vars, create folder to save files
    user_folder = get_user_folder()
    study_folder = secure_filename(form.study_name.data)

    # -------------------------------------------------------------------------
    # save files
    files_dict = {}

    # new user? make folder
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    user_data_folder = os.path.join(user_folder, study_folder)
    if not os.path.exists(user_data_folder):
        os.makedirs(user_data_folder)

    # save files with secure names
    for field, f in files.items():
        filename = secure_filename(f.filename)
        path = os.path.join(user_data_folder, filename)
        print("Saving file to ", path)
        files_dict[field] = filename
        f.save(path)
        f.close()
    # -------------------------------------------------------------------------
    # check uploaded files
    # this import must be here, because get_user_folder is needed by check_files
    from backend.utils.check_uploaded_files import check_files
    status, format_errors = check_files(user_data_folder, files_dict, form)
    if status:
        save_study_to_db(files_dict, form)
        return json.dumps(dict(status='OK'))
    else:
        return json.dumps(dict(status='errors', errors=format_errors))


def save_study_to_db(files_dict, form):
    """
    Saves the paths of files and parameters to the db
    """
    study = models.Studies(author=current_user,
                           study_name=secure_filename(form.study_name.data),
                           skip_variational= bool(form.skip_variational.data),
                           timestamp=datetime.datetime.utcnow())

    # save the path to the files
    for field, f in files_dict.items():
        setattr(study, field, f)
    db.session.add(study)
    db.session.commit()

    # increase total number of studies as well
    current_user.num_studies = current_user.num_studies + 1
    db.session.add(current_user)
    db.session.commit()

# -----------------------------------------------------------------------------
# ANALYSIS - HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def save_analysis(form, study_id):
    """
    Creates analysis folder, calls save_analysis_to_db and write_params_file
    """
    # setup vars to write params file
    user_folder = get_user_folder()
    study = models.Studies.query.get(study_id)
    study_name = study.study_name
    analysis_name = secure_filename(form.analysis_name.data)
    study_folder = os.path.join(user_folder, study_name)
    analysis_folder = os.path.join(study_folder, analysis_name)
    output_folder = os.path.join(analysis_folder, 'output')

    # define dict with all folders, we save it to params later
    folders = {
        "user_folder": user_folder,
        "study_folder": study_folder,
        "analysis_folder": analysis_folder,
        "output_folder": output_folder,
    }

    # create folder for analysis
    if not os.path.exists(analysis_folder):
          os.makedirs(analysis_folder)

    # make output folder
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # write params.csv file
    write_params_file(folders, form, study_id)

    # save analysis to db
    save_analysis_to_db(form, study_id)


def write_params_file(folders, form, study_id):
    """
    Writes the params.csv file which is essential for each analysis to run.
    """
    study = models.Studies.query.get(study_id)

    # create param file
    params_file = os.path.join(folders["analysis_folder"], 'params.csv')
    params = open(params_file, 'w')

    # write header
    params.write(",value\n")

    # write folders
    for k, v in folders.items():
        params.write("%s,%s\n" % (k, v))

    # write studies
    study_fields = ['dataset1', 'dataset2', 'dataset3', 'skip_variational']
    for i, f in enumerate(study_fields):
        field = getattr(study, f)
        if field is not None:
            params.write(f + ',' + str(field) + '\n')

    params.close()


def save_analysis_to_db(form, study_id):
    """
    Saves parameters of analysis and start it on the cluster
    """
    # get if user study has dashboard and combine this with analysis form data
    analysis = models.Analyses(author=current_user,
                               study=models.Studies.query.get(study_id),
                               analysis_name=secure_filename(form.analysis_name.data),
                               status=1,
                               weight_cut=form.weight_cut.data,
                               iterations=form.iterations.data,
                               timestamp_start=datetime.datetime.utcnow())
    db.session.add(analysis)
    db.session.commit()

    # increase total number of studies as well
    current_user.num_analyses = current_user.num_analyses + 1
    db.session.add(current_user)
    db.session.commit()

# -----------------------------------------------------------------------------
# PROFILE - HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def get_studies_array():
    """
    Returns an array of object, so we can display in a popover the files of
    each study on the profile page.
    """
    studies_array = []
    studies = current_user.studies.all()
    for study in studies:
        study_dict = {}

        # get basic info of study
        study_dict['id'] = study.id
        study_dict['study_name'] = study.study_name

        # get files of study
        params = []
        params.append({'field':'Skip Variational', 'value': False})
        study_dict['params'] = params

        files = []
        files_names = ['Dataset 1', 'Dataset 2', 'Dataset 3']
        files_fields = ['dataset1', 'dataset2', 'dataset3']
        for i, f in enumerate(files_fields):
            field = getattr(study, f)
            if field is not None:
                files.append({'field':files_names[i], 'value':field})
        study_dict['files'] = files

        studies_array.append(study_dict)
    return studies_array


def get_analyses_array():
    """
    Returns an array of object, so we can display in a popover the parameters
    of each analysis on the profile page.
    """
    analyses_array = []
    analyses = current_user.analyses.all()
    user_folder = app.config['USER_PREFIX'] + str(current_user.id)
    for analysis in analyses:
        analysis_dict = {}
        # get basic info of analysis
        analysis_dict['id'] = analysis.id
        analysis_dict['analysis_name'] = analysis.analysis_name
        study = models.Studies.query.get(analysis.study_id)
        study_name = study.study_name
        analysis_dict['data_file'] = 'analysis_results'
        analysis_dict['status'] = analysis.status

        # build path for results .zip file
        analysis_folder = os.path.join(user_folder, secure_filename(study_name),
                                       secure_filename(analysis.analysis_name))
        results = analysis.analysis_name + '.zip'
        analysis_dict['results'] = os.path.join(analysis_folder, results)

        # collect all params for the analysis
        params = []
        params.append({'field':'Study name', 'value': study_name})
        param_names = ['Weight Cut', 'Iterations']
        param_fields = ['weight_cut', 'iterations']

        for i, p in enumerate(param_fields):
            field = getattr(analysis, p)
            if field is not None:
                params.append({'field':param_names[i], 'value':field})
        analysis_dict['params'] = params

        analyses_array.append(analysis_dict)
    return analyses_array

# -----------------------------------------------------------------------------
# GENERAL - HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def security_check(user_id, study_id, analysis=False):
    """
    For a couple of views, we need to make sure that the user is accessing
    content that is his/her and not others.
    """
    # check if user is trying to access a dataset that's not theirs
    user_ok = user_id == current_user.id

    # check if the study belongs to the user
    study_ok = False

    # if delete analysis was clicked, we need to check analyses and analysis_id
    if analysis:
        studies = current_user.analyses.all()
    else:
        studies = current_user.studies.all()
    for study in studies:
        if study.id == study_id:
            study_ok = True
    return user_ok * study_ok


def get_user_folder():
    """
    Returns the folder of the current user, based on the config params.
    """
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'],
                               app.config['USER_PREFIX'] +
                               str(current_user.id))
    return user_folder


def get_study_folder(study_id):
    """
    Returns a path to the current user's study
    """
    user_folder = get_user_folder()
    study = models.Studies.query.get(study_id)
    study_name = study.study_name
    study_folder = os.path.join(user_folder, study_name)
    return study_folder

# -----------------------------------------------------------------------------
# RESULTS - RENDERING MODELS
# -----------------------------------------------------------------------------

def get_ensemble_values(cbi_output_file):
    """
    Returns a path to the current user's study
    """
    cbi_out = open(cbi_output_file)
    model_names = []
    model_weights = []
    model_sem = []
    model_sd = []
    model_neff = []
    model_rhat = []
    lines = cbi_out.readlines()
    for line in lines:
        result_row = line.split(':')
        pdb_name = result_row[0]
        if pdb_name[-3:] == 'pdb':
            model_names.append(pdb_name)
        else:
            break
        model_weights.append(round(float(result_row[1]),2))
        model_sem.append(round(float(result_row[2]),2))
        model_sd.append(round(float(result_row[3]), 2))
        model_neff.append(round(float(result_row[4]),1))
        model_rhat.append(round(float(result_row[5]),1))
    cormap_string = lines[-1].split(":")[1].strip()[4:-1]
    model_evidence = float(lines[-2].split(":")[1])
    chi2 = float(lines[-3].split(":")[1])
    jsd = float(lines[-4].split(":")[1])

    return model_names, model_weights, model_sem, model_sd, model_neff, model_rhat, \
           model_evidence, chi2, jsd, cormap_string
