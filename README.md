[comment]: # "Auto-generated SOAR connector documentation"
# JASK

Publisher: JASK Labs Inc  
Connector Version: 1\.0\.0  
Product Vendor: JASK  
Product Name: ASOC Platform  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 4\.0\.1068  

This app implements ingest action for fetching alerts on JASK ASOC Platform

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a ASOC Platform asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api\_user** |  required  | string | API Username
**api\_key** |  required  | password | User API Key
**login\_url** |  required  | string | Login URL

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[on poll](#action-on-poll) - Callback action for the on\_poll ingest functionality  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'on poll'
Callback action for the on\_poll ingest functionality

Type: **ingest**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start\_time** |  optional  | Start of time range, in epoch time \(milliseconds\) | numeric | 
**end\_time** |  optional  | End of time range, in epoch time \(milliseconds\) | numeric | 

#### Action Output
No Output