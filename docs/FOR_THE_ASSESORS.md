
# For The Assessors

## Group Members

ANDREW JORDAN - A-MJordan
EMILY AMIES - “Ubuntu”, Emily-Amies
GREG ROWLAND - growland2

All group members contributed to the documentation equally.

AI was used (ChatGPT/Co-Pilot) to query code structure and to assist in generating docstrings in a PEP-8 compliant manner.

## Sprint Notes

### Initial Requirements Gathering

Annotate variants

* What annotation is required?
* Consensus classification - absolute requirement
* Star rating
* HGVS c notation for MANE transcript - absolute requirement
* Clinical indication
* Count of submissions 
* Plus anything else use
* What are the annotation data going to be used for? 
* Manual notes custom free text?
* What is the input data by?
* One VCF and CSV per sample 
* Types of variants
* Is data manually ingested or via file
* How will annotation data be retrieved?
* Static local file vs API calling 

Create a searchable resource

* How does the user search the resource (database)? / What is the fundamental unit of this resource - patients or variants?
* Search by patient ID
* Search by gene
* What needs to be returned from search?
* How many patients have variant in gene?
* What classification?
* Access to searchable research?
* Nice to have: search via GUI
* Excel would be sufficient

Misc

* Aim of their research / overarching needs
* Audit trail / documentation
* Information governance / data privacy 
* Documentation
* Quality assurance - how do we know the correct annotation data has been generated, and how do we know the correct 

https://www.ncbi.nlm.nih.gov/clinvar/docs/maintenance_use/#api
https://www.ncbi.nlm.nih.gov/books/NBK25497/#
https://stackoverflow.com/questions/63121584/how-to-use-entrezpy-and-biopython-entrez-libraries-to-access-clinvar-data-from-g#
https://github.com/krassowski/easy-entrez

Validated variants output:

* Column name = “t_hgvs”
* Outfile name = “validated_variants.csv”

Clinvar annotation endpoint:
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=clinvar&id=65533&retmode=json

UID finder for variants:

Implementation:

* Example project repo: https://github.com/Peter-J-Freeman/SeqKitSTP2025
* Project repo: https://github.com/Emily-Amies/parkVar
* Trello: ParkVar | Trello

**Epic Story:**
As a Clinical Researcher, I want to annotate and store germline variants from a Parkinsons NGS panel for an academic research project. 

### Sprint 1 Review

Sprint 1 review - 5/11/25

Internal Reflection:

We have developed a minimal viable product as a functional front end which takes input CSV format variant data and provides the functionality to validate variants using an API callout to variantvalidator followed by calling an API from NCBI’s ClinVar via the eutilis/esummary function.

Questions:

* What transcripts do you want annotation returned for?
    * Only interested in MANE Select 
    * Protein change 
    * Gene symbol?
    * See them all at the same time
    * Looks good for now - would like to be able to download the data
    * All relevant clinical indication  
    * Potentially variant/population frequency if possible?
* Do you want to filter data? If so how?
    * See them all at the same time
    * Search by patient ID 
    * By gene 
* Does you want to be able to download the filtered/annotated variants?
    * Quite nice to download but not too bothered 
* Go over initial requires - check they are the same or if any changes have occurred 
    * Unchanged
* What happens if variant description in input is invalid?
    * Show them but with flag to say invalid - dont want to lose data


Feedback:

* Only accepting CSVs atm is this ok?
* Looks good for now - would like to be able to download the data
* Minimum requirements:
    * Full HGVS g, c and p dot with reference genome 
    * HGNC gene id and symbol
* Nice to have:
    * MIM ID and MIM name for all relevant clinical indications
* Cross-reference ClinVar vs VV variant descriptions 


### Sprint 2 Review

Internal reflection:

* Consider user/customer requirements during product owner/user meetings to try and identify potential issues that may arise when trying to achieve each one (involves a little bit of prior anticipation of what features/requirements the customer may raise). This helps mitigate “agreeing” to a requirement, or giving the customer the impression that the requirement will be met, then reporting back negatively at a future sprint/iteration.
* For the customer meetings and capturing requirements - always good to have pens and paper available to allow more visual/dynamic user stories

Questions for customer:

* Filtering options?
* Transcript ID - Ensembl vs refseq?
* Clinical indication taking first one - is this okay?
* Further annotation sources? 
* WHAT IS THE HIGHEST VALUE NEXT STEP/REQUIREMENT?
    * SEARCH Functionality

Feedback:

* Filter bar at the top from start
* T_hgvs more important than g_hgvs
* Maybe be able to select columns to view (don’t need ID column)
* Don’t need disease MIM necessarily 
* Don’t need HGNC IDs to be displayed
* Search functionality would be lovely

Sprint 3 Planning:

* Refactor and streamline code to allow for better human readability, more granular doc-strings and simpler implementation of unit testing.
* Finalise all error handling and logging 
* Implement unit testing (Pytest) and integration testing (Jenkins - latest log file)
* Containerisation (Docker)
* Formatting (PEP8 incl. docstrings)
* Documentation (operation.md, installation.md, technical.md)

### Sprint 3 Review 

Sprint 3 Review - 10/12/2025

Internal Reflection:

While there are some additional functional requirements put forth by the customer in the previous sprint review (e.g. search functionality, persistent data structure - i.e. SQL database), given that this is our final sprint we want to focus on the non-functional aspects of the projects (testing, documentation, containerisation etc.). With additional time and future sprints, these functional aspects would be addressed.

Questions for customer:

* How would you like to view the data within the uploaded dataset? (rows v column filters, searchable data, etc)
* What is your preferred way of interacting with the data (downloadable csv vs direct interaction with the dataframe/database, etc.)
* Are there any particular requirements for the front end we haven’t captured?

Feedback:

* New layout is better (filter button location and column order)
* Human readability of data could be improved (left justification, inappropriate floating point numbers that should be strings)
* Ability to filter columns would also help with data readability
* Persistence of data would be the biggest requirement moving forward
* Ability to upload and annotate multiple CSVs at a time would be beneficial
