'''
Wildlife Fisheries Setup Tool Module
Description: Automate creation of folders and shapefiles for Wildlife Authorizations
Author: Fish and Wildlife Authorizations Geospatial Services, GEOBC
Version 3.2 - Converted to Python Toolbox tool class format
'''
import arcpy
import datetime
import os
import sys


class WildlifeFisheriesSetupTool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Wildlife Fisheries Setup"
        self.description = "Automate creation of folders and shapefiles for Wildlife Authorizations"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        # Parameter 0: Tenure/File Number
        param0 = arcpy.Parameter(
            displayName="Tenure Number",
            name="file_num",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        # Parameter 1: Area of Interest to Append
        param1 = arcpy.Parameter(
            displayName="Area of Interest (to append)",
            name="append_aoi",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")
        
        # Parameter 2: Permit Type
        param2 = arcpy.Parameter(
            displayName="Permit Type",
            name="permit_type",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        param2.filter.type = "ValueList"
        param2.filter.list = [
            "Guide Outfitter",
            "Nuisance Salvage",
            "Scientific Fish Collection",
            "Transporter License",
            "Traplines",
            "Vehicle Exemption",
            "Private Property Trapping License",
            "Wildlife Habitat Area",
            "General Wildlife"
        ]
        
        # Parameter 3: Output Folder (Derived)
        param3 = arcpy.Parameter(
            displayName="Output Folder",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Derived",
            direction="Output")
        
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        # Get parameters
        file_num = parameters[0].valueAsText
        append_aoi = parameters[1].valueAsText
        permit_type = parameters[2].valueAsText
        
        # Initialize progress bar
        arcpy.SetProgressor("default", "Setting up wildlife authorization...")
        
        # Set environment
        arcpy.env.workspace = r"\\spatialfiles.bcgov\work\srm\gss\authorizations\wildlife"
        arcpy.env.overwriteOutput = False
        
        # Calculate date variables
        date = datetime.date.today()
        year = str(date.year)
        
        # Set variables
        base = arcpy.env.workspace
        baseYear = os.path.join(base, year)
        
        # Permit type mapping
        permit = {
            "Guide Outfitter": "guide_outfitter",
            "Nuisance Salvage": "nuisance_salvage",
            "Scientific Fish Collection": "scientific_fish_collection",
            "Transporter License": "transporter_license",
            "Traplines": "traplines",
            "Vehicle Exemption": "vehicle_exemption",
            "Private Property Trapping License": "private_property_trapping_license",
            "Wildlife Habitat Area": "wildlife_habitat_area",
            "General Wildlife": "general_wildlife"
        }
        
        # Get permit folder path
        if permit_type not in permit:
            arcpy.AddError(f"ERROR: Invalid permit type '{permit_type}'")
            return
        
        basePermit = os.path.join(baseYear, permit[permit_type])
        arcpy.AddMessage(f"Base permit directory: {basePermit}")
        
        # Setup output variables
        outName = file_num.upper()
        geometry = "POLYGON"
        template = r"\\spatialfiles.bcgov\work\srm\gss\resources\tools\authorizations\wildlife\source_data\BLANK_polygon.shp"
        m = "SAME_AS_TEMPLATE"
        z = "SAME_AS_TEMPLATE"
        
        # Check if template exists
        if not arcpy.Exists(template):
            arcpy.AddError(f"ERROR: Template shapefile not found: {template}")
            return
        
        spatialReference = arcpy.Describe(template).spatialReference
        
        # ===========================================================================
        # Create Folders
        # ===========================================================================
        arcpy.SetProgressorLabel("Creating folders...")
        arcpy.AddMessage(" ")
        arcpy.AddMessage("Creating folders . . .")
        
        fileFolder = os.path.join(basePermit, outName)
        shapeFolder = fileFolder
        outPath = shapeFolder
        
        if os.path.exists(fileFolder):
            arcpy.AddMessage(f"{outName} folder already exists.")
        else:
            os.makedirs(fileFolder)
            arcpy.AddMessage(f"Created folder: {fileFolder}")
        
        # ===========================================================================
        # Create Shapefile(s) and add them to the current map
        # ===========================================================================
        arcpy.SetProgressorLabel("Creating shapefile...")
        arcpy.AddMessage(" ")
        arcpy.AddMessage("Creating Shapefiles . . .")
        
        output_shapefile = os.path.join(outPath, outName + ".shp")
        
        if os.path.isfile(output_shapefile):
            arcpy.AddWarning(f"{output_shapefile} already exists")
            arcpy.AddWarning("Exiting without creating files")
            return
        else:
            # Creating feature class
            arcpy.AddMessage(f"Creating shapefile: {output_shapefile}")
            create_shp = arcpy.management.CreateFeatureclass(
                outPath, outName, geometry, template, m, z, spatialReference)
            
            # Append the newly created shapefile with area of interest
            arcpy.AddMessage("Appending area of interest...")
            append_shp = arcpy.management.Append(append_aoi, create_shp, "NO_TEST")
            arcpy.AddMessage("Append Successful")
            
            # Create KML
            arcpy.SetProgressorLabel("Creating KML...")
            create_kml = os.path.join(outPath, outName + ".kml")
            
            # Make layer for KML conversion
            layer_shp = arcpy.management.MakeFeatureLayer(append_shp, outName)
            
            # Convert to KML
            arcpy.conversion.LayerToKML(layer_shp, create_kml)
            arcpy.AddMessage(f"KML created: {create_kml}")
        
        # ===========================================================================
        # Add data to the map
        # ===========================================================================
        arcpy.SetProgressorLabel("Adding data to map...")
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        aprxMap = aprx.activeMap
        
        if aprxMap is None:
            arcpy.AddWarning("No active map to add the data to.")
        else:
            arcpy.AddMessage("Adding data to the active map.")
            aprxMap.addDataFromPath(output_shapefile)
        
        # ===========================================================================
        # Completion message
        # ===========================================================================
        arcpy.ResetProgressor()
        arcpy.AddMessage(" ")
        arcpy.AddMessage(" ")
        arcpy.AddMessage("===========================================================================")
        arcpy.AddMessage(f"{fileFolder}, is ready for processing.")
        arcpy.AddMessage("===========================================================================")
        arcpy.AddMessage(" ")
        arcpy.AddMessage(f"<a href='file:///{fileFolder}'>Click here to open output folder</a>")
        
        # Set the derived output parameter
        parameters[3].value = fileFolder
        
        return
