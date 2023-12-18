
# S-values 

The MIRD S-values are extracted from the Opendose website. 
The following are the command lines used to retrieve the information.
The obtained data are stored in the data folder, you should not have to use those tools except if additional ROI are needed. 

The following lines retrieve the list of source and isotopes available for the two main ICRP phantoms. 

        opendose_web_get_sources_list -o opendose_sources.json -p "ICRP 110 AM"
        opendose_web_get_isotopes_list -o opendose_isotopes.json -p "ICRP 110 AM"
        opendose_web_get_sources_list -o opendose_sources.json -p "ICRP 110 AF"     
        opendose_web_get_isotopes_list -o opendose_isotopes.json -p "ICRP 110 AF" 

The following extract the S-values for the given isotope (Lu177) and few ROIS. The resulting values are stored in json files in the data folders.

        opendose_web_get_svalues -r lu177 -s "liver" -p "ICRP 110 AM"
        opendose_web_get_svalues -r lu177 -s "spleen" -p "ICRP 110 AM"
        opendose_web_get_svalues -r lu177 -s "right kidney" -p "ICRP 110 AM"
        opendose_web_get_svalues -r lu177 -s "left kidney" -p "ICRP 110 AM"

        opendose_web_get_svalues -r lu177 -s "liver" -p "ICRP 110 AF"               
        opendose_web_get_svalues -r lu177 -s "spleen" -p "ICRP 110 AF"
        opendose_web_get_svalues -r lu177 -s "right kidney" -p "ICRP 110 AF"
        opendose_web_get_svalues -r lu177 -s "left kidney" -p "ICRP 110 AF"


