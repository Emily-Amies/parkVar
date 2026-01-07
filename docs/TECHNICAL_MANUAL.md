# TECHNICAL MANUAL

The design intentionally separates tasks across three components:

- **Flask app** - forms the backbone of the app, handles input and coordinates the validation and annotation process
- **Validation** - validates variants through the VariantValidator API
- **Annotation** - annotates variants using the Clinvar API

This separation improves testability and allows for components to be developed separately.

# Flask

## Accessing the app

The Flask application is accessed through `main.py` which deletes all files in the `/data` directory. This is because temporary files are written to this directory and failure to delete the files would result in them crossing over into the next session.

`main.py` also checks if a logs directory is present as this is not included in the git repository.

The script imports the flask app from `flask_app.py` and runs it.

---

## Flask application design

`flask_app.py` is the coordinating script for the app. It is responsible for handling HTTP requests, interaction with the user and orchestrating the flow of information through the validation and annotation steps.

It is accompanied by several helper scripts and a utility script. The helper scripts are named after each route in the app: `upload`, `annotate` and `filter`. The utility script stores the HTML templates and custom exceptions.

---

### Route overview

The application has four routes, each corresponding to a specific user action:

- `/`
  This is the main rout that renders the application homepage. From here, users can upload CSV files, trigger annotation, and view results.

- `/annotate`
  This route is triggered when the user clicks the `Annotate` button. It coordinates the validation and annotation workflow by calling methods from the validation script (`validate.py`) and the annotation script (`clinvar_annotator.py`). Results are rendered as a table.

- `/filter`
  This route applies user-selected filters, currently only patient ID, to the annotated results and updates the results table accordingly.

- `/refresh`
  This route resets the app, clearing files in `/data` so that a new session can be started.

---

### Data flow through the Flask application

The figure below shows the flow of data through the app and options available to the user at each stage.

1. The user enters the application at `/`, which displays the **Upload** and **Refresh Session** buttons. Once a file has been uploaded:

   - The input CSV is read and converted into a pandas DataFrame.
   - The name of the file is appended to `uploaded_files.txt`. This is used to track which files have been uploaded so that duplicate uploads can be detected and a warning message displayed.
   - The data from the pandas DataFrame is written to an input data file, `input_data.csv`.
   - The user can upload an additional file using **Upload**.
   - The **Annotate** button becomes available.
   - The **Refresh Session** button remains available.

2. When the user selects **Annotate**, the annotation workflow is triggered via the `/annotate` route:

   - `validate.py` validates the variants in `input_data.csv` and outputs `validated_data.csv` (see below for details).
   - `clinvar.py` then annotates the data in `validated_data.csv` to produce `anno_data.csv` (see below for details).
   - The annotated data is displayed as a table in the web interface.
   - Unique patient IDs are collected from the data and displayed as selectable checkboxes.
   - The **Upload** button is no longer available.
   - The **Filter** button becomes available.
   - The **Refresh Session** button remains available.

3. The user can select one or more patient IDs using the checkboxes and select **Filter**, which triggers the `/filter` route:

   - `anno_data.csv` is converted into a pandas DataFrame, filtered based on the selected patients, and written to `filtered_data.csv`.
   - The filtered results are displayed as a table in the web interface.
   - The **Annotate** button is no longer available.
   - The **Filter** and **Refresh Session** buttons remain available.

![Flowchart showing organisation of the flask app](images/flow.png | wwidth=400)

# Variant validation
Variant validation and gathering of valid variant descriptions (e.g. HGVSg, HGVSc, HGVSp, HGNC ID and symbol etc) is performed via the [validate.py](../parkVar/modules/validate.py) module. To do so, the module:

1. Reads variant data from a CSV file containing '#CHROM', 'POS', 'REF' and 'ALT' columns and initialises a DataFrame using these columns form the input CSV as well as additional columns to contain further variant descriptions/annotation gathered by this module.
2. Calls the Variant Validator API for each variant in the Dataframe.
3. Parses and validates the API responses, extracting key fields such as genomic/transcript/protein HGVS, gene symbol, and HGNC ID etc.
4. Updates the DataFrame with validated values where possible.
5. The final DataFrame containing validated variant descriptions is outputted to a CSV.

For developers, if you wish to run this module in isolation, this can be done by providing an input CSV and output file name and executing the following example command from the project's root directory:

```bash
python -m parkVar.modules.validate <input_csv_path> <output_csv_path>
```

# Variant annotation
The clinvar_annotator.py module handles the variant annotation stage of the workflow and is comprised of the following main steps:

1. Defining the inputs and constants for use in future steps

* EUTILS_BASE sets the base entrez URL for querying ClinVar via the eutils API route.

* NCBI_RATE_LIMIT_SLEEP defines a delay period between API requests to adhere to the 3 requests per second limit set by NCBI.

* REVIEW_STATUS_TO_STARS converts the textual review status for each clinical submission (as determined through the returned JSON) into a the "star rating" that is displayed on the ClinVar website.

2. Using the HGVS description of each called variant output from the validate.py module, ClinVar is queried to generate the associated UID, which is appended to the EUTILS_BASE URL to search for and retrieve the ClinVar esummary and extract the required fields.

* search_hgvs takes the HGVS field from the output_csv from validate.py and returns the first matching ClinVar UID (or an empty field if no match/error)

* fetch_esummary takes the returned ClinVar UID and appends it onto the EUTILS_BASE URL, then using the "/esummary.fcgi" returns the associated ClinVar esummary in JSON format (line 141: "retmode": "json" - can be altered for different return format, but JSON is preferrable).

* extract_disease_from_trait_set pulls the associated disease name and OMIM ID from the first ClinVar submission. May want to expand these sections in future to account for multiple ClinVar submissions, or incorporate key terms to limit data to Parkinsons associated traits.

* extract_consensus_and_stars pulls the textual clinical significance data from the esummary, and uses the REVIEW_STATUS_TO_STARS definitions to assign the appropriate star rating. Due to changes in the ClinVar esummaries in ~2021, which moved from a single "clinical_significance" field, to two fields split based on oncological vs germline implications (which will appear mutually exclusively depending on the last time the submission was updated), this function will search for both "germline_classification" for newer submissions, and "clinical_significance" for legacy entries.

3. The data extracted from the previous step is used to repopulate the output_csv dataframe from the validate.py module including the ClinVar annotation information. 

4. This is the main logic for this module that pulls all the previous functions into functions that can be called from the flask_app.py module as part of the parkVar.main workflow
