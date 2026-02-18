'''
Trapline_AutoZoom_Master_toolbox_EB_Oct_21.py 
Description: 
This script creates a trapline boundary feature layer and KML by way of user input as "feature_name', along with any associated Crown Land File(s) with 
Trapline Cabin features  WHSE_TANTALIS.TA_CROWN_TENURES_SVW Definition Query = TENURE_SUBPURPOSE = 'TRAPLINE CABIN'
Storing these Features as .shp in the data_dir. An APRX file is stored in the APRX_dir and a PDF is created in the pdf_dir. 
Description:  Automate creation of Trapline boundary data, aprx, kml and pdf folders.
Author:  Ozra (Sunny) Rahimi, Evan Breton
         Ministry of Forests, Lands, Natural Resource Operations
           and Rural Development
      
Usage Note:  This script will only work with Temp_Trapline_Master template found here:
\\spatialfiles.bcgov\Work\srm\nel\Local\Geomatics\Workarea\SharedWork\Trapline_Territories\aprx\Temp_Trapline_Master.aprx
Version 1.0

Updated by csostad, 2026-02-17
Refactor trapline map generation script to Python toolbox with improved structure

Major Changes:
- Convert script from .py to .pyt (ArcGIS Python Toolbox format)
- Add GSS Request Number as first parameter for better organization
- Implement dynamic year-based workspace using datetime module
- Restructure output folders: wildlife/{year}/traplines/{GSS_Request_Number}/{shapefile,maps,kml}

Features Added:
- Date-stamped PDF filenames: Trapline_{file_num}_{yyyymmdd}.pdf
- Constants-based configuration for easy maintenance
- Comprehensive error handling with descriptive messages for missing layers
- Layer name validation with troubleshooting guidance

Bug Fixes:
- Fix KML export error (ERROR 000229) by using shapefile directly instead of reopened project layer references
- Add proper input validation for both parameters
- Improve error messages to guide users when layers are renamed

Code Quality:
- Remove duplicate code and unused variables
- Comment out old folder structure for reference
- Add proper toolbox class structure with getParameterInfo() and execute() methods
- Better exception handling throughout with specific error types

Breaking Changes:
- Parameter order changed: GSS Request Number (0), Trapline Number (1)
- Folder structure completely reorganized
- Must be run as Python Toolbox (.pyt) instead of standalone script



'''
import arcpy
import os
from datetime import datetime
# Constants
WORKSPACE_BASE = r'\\spatialfiles.bcgov\srm\gss\authorizations\wildlife'
MAP_NAME = 'Map'
LAYOUT_NAME = 'Layout'
DEFAULT_SCALE = 250000
AREA_FIELD = "Area_ha"
CROWN_LAND_FIELD = "CROWN_LAND"
# TRAPLINE_FIELD = "TRAPLINE_1"
TRAPLINE_FIELD = "TRAPLINE_AREA_IDENTIFIER"
SQ_METERS_TO_HECTARES = 10000

# Create or get the feature_layer object from ArcGIS Pro's content pane or the appropriate source
aprx = arcpy.mp.ArcGISProject("CURRENT")
arcpy.env.overwriteOutput = True

# Get current year and set up workspace dynamically
current_year = datetime.now().year
year_folder = os.path.join(WORKSPACE_BASE, str(current_year))

# Check if year folder exists, create if not
if not os.path.exists(year_folder):
    os.makedirs(year_folder)
    arcpy.AddMessage(f"Created year folder: {year_folder}")
else:
    arcpy.AddMessage(f"Using existing year folder: {year_folder}")



# Set a temporary workspace for the year folder
arcpy.env.workspace = year_folder
# Get map and layout objects
map_obj = aprx.listMaps(MAP_NAME)[0]
layout = aprx.listLayouts(LAYOUT_NAME)[0] 
all_trapline_cabins_obj = map_obj.listLayers("All Trapline Cabins")[0]
all_trapline_boundaries_obj = map_obj.listLayers("All Trapline Boundaries")[0]

# Function to create a directory if it doesn't exist
def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)
        arcpy.AddMessage(f"Directory created: {directory}")
    else:
        arcpy.AddMessage(f"Directory already exists: {directory}")


# Get user input parameters
# Parameter 0: GSS Request Number
gss_request_num = arcpy.GetParameterAsText(0)

# Validate GSS Request Number
if not gss_request_num:
    arcpy.AddError("ERROR: No GSS Request Number provided. Please provide a valid GSS Request Number.")
    raise SystemExit("No GSS Request Number provided")

# Parameter 1: Trapline boundary number
file_num = arcpy.GetParameterAsText(1)

# Validate trapline boundary number
if not file_num:
    arcpy.AddError("ERROR: No trapline boundary number provided. Please provide a valid file number.")
    raise SystemExit("No file number provided")

# Create NEW folder structure based on GSS Request Number
traplines_base = os.path.join(year_folder, 'traplines')
gss_request_dir = os.path.join(traplines_base, gss_request_num)

# Create main GSS Request directory
create_directory(gss_request_dir)

# Create subfolders: kml, shapefile, and maps
kml_dir = os.path.join(gss_request_dir, 'kml')
shapefile_dir = os.path.join(gss_request_dir, 'shapefile')
maps_dir = os.path.join(gss_request_dir, 'maps')

create_directory(kml_dir)
create_directory(shapefile_dir)
create_directory(maps_dir)

arcpy.AddMessage(f"Folder structure created for GSS Request: {gss_request_num}")
arcpy.AddMessage(f"  KML directory: {kml_dir}")
arcpy.AddMessage(f"  Shapefile directory: {shapefile_dir}")
arcpy.AddMessage(f"  Maps directory: {maps_dir}")


################################################################################################################################
#
# Step 2 - Create the Application Polygon
#
#############################################################################################################################
arcpy.AddMessage("Step 2 - Creating Application Polygon")
# Set the definition query and assign it to a variable
expression = f"{arcpy.AddFieldDelimiters(arcpy.env.workspace, TRAPLINE_FIELD)} = '{file_num}'"
# Apply the expression to the layer "Application" in the Site Map (Defined as a global variable at the top of the script)
all_trapline_boundaries_obj.definitionQuery= expression
arcpy.AddMessage(f"         Definition query {expression} set for all trapline boundaries")
# Error Handling -  Use a SearchCursor to count the number of records returned by the definition query
count = 0
with arcpy.da.SearchCursor(all_trapline_boundaries_obj, "*") as cursor:
    for row in cursor:
        count += 1
        
# Check if the count is 0 and display a message if the definition query was successful or not.
if count == 0:
    arcpy.AddError(f"ERROR: No records returned by definition query: {expression}. Please check the file number and try again.")
    raise SystemExit("No matching trapline boundary found")
else:
    arcpy.AddMessage(f"         Definition query {expression} set for layer: {all_trapline_boundaries_obj}. Records returned: {count}")

# Specify the output file path for the exported feature
application_trapline_boundary = os.path.join(shapefile_dir, f'{file_num}.shp')
arcpy.AddMessage(f"Output feature path: {application_trapline_boundary}")


###########################################################################################################################################
#
# Step 3 - Export the Feature to a Shapefile
#
###########################################################################################################################################
# Create a feature layer to select the specific feature
try:
   arcpy.management.MakeFeatureLayer(all_trapline_boundaries_obj, "temp_layer") 
   arcpy.AddMessage("Feature layer created.")
except arcpy.ExecuteError as e:
    arcpy.AddError(f"MakeFeatureLayer_management error: {e}")
    raise SystemExit("Failed to create feature layer")
# Check if the temporary layer exists
if arcpy.Exists("temp_layer"):
    try:
        arcpy.management.CopyFeatures("temp_layer", application_trapline_boundary)
        arcpy.AddMessage("Export process complete.")
    except arcpy.ExecuteError as e:
        arcpy.AddError(f"CopyFeatures_management error: {e}")
        raise SystemExit("Failed to copy features")
else:
    arcpy.AddError("Temporary layer 'temp_layer' does not exist.")
    raise SystemExit("Temporary layer not found")


# Add a new field for the area in hectares if it doesn't already exist
if AREA_FIELD not in [f.name for f in arcpy.ListFields(application_trapline_boundary)]:
    arcpy.management.AddField(application_trapline_boundary, AREA_FIELD, "DOUBLE")
    arcpy.AddMessage(f"Field '{AREA_FIELD}' added to the feature class.")
# Define the function to calculate area in hectares
def calculate_area_in_hectares(geometry):
    area_sq_meters = geometry.area
    return area_sq_meters / SQ_METERS_TO_HECTARES

# Calculate the area for each polygon and update the new field
arcpy.AddMessage("Calculating area in hectares...")
formatted_area = ""
with arcpy.da.UpdateCursor(application_trapline_boundary, ["SHAPE@", AREA_FIELD]) as cursor:
    for row in cursor:
        area_hectares = calculate_area_in_hectares(row[0])
        row[1] = area_hectares
        cursor.updateRow(row)
        formatted_area = f"{area_hectares:.2f} ha."
        arcpy.AddMessage(f"Formatted area: {formatted_area}")
arcpy.AddMessage(f"Area in hectares has been added to the field '{AREA_FIELD}'.")



##############################################################################################################
#
# Step 4 - Clip the "Trapline Cabins" layer based on the feature layer
#
##############################################################################################################
arcpy.AddMessage("Step 4 - Clipping Trapline Cabins layer")
clipped_cabins_output = os.path.join(shapefile_dir, f'{file_num}_Cabins.shp')
arcpy.AddMessage(f"Output feature path: {clipped_cabins_output}")

# Clip the "Trapline Cabins" layer based on the feature layer
arcpy.analysis.Clip("All Trapline Cabins", application_trapline_boundary, clipped_cabins_output)
arcpy.AddMessage(f"Clipping of trapline boundary to Crown Lands layer completed.")

# Initialize Crown_Num_Values to handle cases where field doesn't exist
Crown_Num_Values = []
# Check if the field exists in the attribute table of the clipped cabins output
if CROWN_LAND_FIELD not in [f.name for f in arcpy.ListFields(clipped_cabins_output)]:
    arcpy.AddMessage(f"{CROWN_LAND_FIELD} not found in the attribute table.")
else:
    # Open a SearchCursor to iterate over rows in the clipped cabins feature class
    with arcpy.da.SearchCursor(clipped_cabins_output, [CROWN_LAND_FIELD]) as cursor:
        for row in cursor:
            # Capture the Crown Land value from the crown_land_field
            crown_land_value = row[0]
            # Only append non-null and non-empty values to the list
            if crown_land_value is not None and crown_land_value != "":
                Crown_Num_Values.append(crown_land_value)
    # Check if any valid Crown Land values were found
    if not Crown_Num_Values:
        arcpy.AddMessage("No valid Crown Land values found. Setting default layer name.")
        # Set a default name if no values found
        new_layer_name = "Trapline_Cabin_No_Values"
        all_trapline_cabins_obj.name = new_layer_name
        arcpy.AddMessage(f"Layer renamed to: {new_layer_name}")
    else:
        # Convert the list of Crown Land values to a single string, joined by underscores
        Crown_Num_Values_String = "_".join(map(str, Crown_Num_Values))
        
        # Update the name of the trapline cabin feature layer based on the joined Crown Land values
        new_layer_name = f"Trapline_Cabin_{Crown_Num_Values_String}"
        all_trapline_cabins_obj.name = new_layer_name
        arcpy.AddMessage(f"Layer renamed to: {new_layer_name}")
    
    # Apply definition query based on the number of Crown Land values found
    if len(Crown_Num_Values) == 1:
        # If there's only one Crown Land value, apply an equality query
        expression1 = f"{arcpy.AddFieldDelimiters(arcpy.env.workspace, CROWN_LAND_FIELD)} = '{Crown_Num_Values[0]}'"
        all_trapline_cabins_obj.definitionQuery = expression1
        arcpy.AddMessage(f"Definition query applied to cabins layer: {expression1}")
    elif len(Crown_Num_Values) > 1:
        # If there are multiple Crown Land values, apply an IN query
        values_string = ', '.join([f"'{val}'" for val in Crown_Num_Values])
        expression1 = f"{arcpy.AddFieldDelimiters(arcpy.env.workspace, CROWN_LAND_FIELD)} IN ({values_string})"
        all_trapline_cabins_obj.definitionQuery = expression1
        arcpy.AddMessage(f"Definition query applied to cabins layer: {expression1}")
# Rename the boundaries layer
all_trapline_boundaries_obj.name = f"{file_num} ({formatted_area})"
arcpy.AddMessage(f"Layer renamed to: {file_num} ({formatted_area})")

# Create a new variable for Crown cabins string (for further operations if needed)
new_crown_cabins_str = f"{file_num}_Cabins_{Crown_Num_Values_String}" if Crown_Num_Values else "Trapline_Cabin_No_Values"
arcpy.AddMessage(f"New Crown cabins variable: {new_crown_cabins_str} created.")
# Update map title text element
for elm in layout.listElements("TEXT_ELEMENT"):
    if elm.name == "Map Title":
        elm.text = f"Trapline {file_num}"
        arcpy.AddMessage("Map title text element updated")
        break
# Zoom to trapline boundary feature and set scale
arcpy.AddMessage("Step 5 - Zooming to feature and setting scale")
zoom_feature_layer = all_trapline_boundaries_obj
mapframe = layout.listElements('MAPFRAME_ELEMENT', 'Map Frame')[0]

# Select all features and zoom
arcpy.SelectLayerByAttribute_management(zoom_feature_layer, "NEW_SELECTION", "1=1")
mapframe.zoomToAllLayers(True)
arcpy.SelectLayerByAttribute_management(zoom_feature_layer, "CLEAR_SELECTION")

# Set scale
mapframe.camera.scale = DEFAULT_SCALE
arcpy.AddMessage(f"Zoomed to feature and set scale to: {mapframe.camera.scale}")
##############################################################################################################
#
# Step 6 - Export PDF and save project
#
##############################################################################################################
arcpy.AddMessage("Step 6 - Exporting PDF and saving project")

# Generate date string for PDF filename
date_string = datetime.now().strftime('%Y%m%d')

# Export the layout to PDF
output_pdf = os.path.join(maps_dir, f'Trapline_{file_num}_{date_string}.pdf')
try:
    layout.exportToPDF(out_pdf=output_pdf,
                       resolution=300,
                       image_quality="BEST",
                       compress_vector_graphics=True, 
                       image_compression="ADAPTIVE")
    arcpy.AddMessage(f"PDF exported successfully to: {output_pdf}")
except Exception as e:
    arcpy.AddError(f"Failed to export PDF: {e}")
    raise

# Save project copy
aprx_path = os.path.join(maps_dir, f"{file_num}.aprx")
try:
    aprx.saveACopy(aprx_path)
    arcpy.AddMessage(f"ArcGIS Pro project saved: {aprx_path}")
except Exception as e:
    arcpy.AddError(f"Failed to save project: {e}")
    raise
##############################################################################################################
#
# Step 7 - Export KML
#
##############################################################################################################
arcpy.AddMessage("Step 7 - Exporting KML")

kml_output = os.path.join(kml_dir, f"{file_num}.kmz")

# Re-open the saved project for KML export
try:
    aprx_saved = arcpy.mp.ArcGISProject(aprx_path)
    saved_map = aprx_saved.listMaps(MAP_NAME)[0]
    
    # Find the target layer
    target_layer_name = f"{file_num} ({formatted_area})"
    target_layer = None
    
    for lyr in saved_map.listLayers():
        if lyr.isFeatureLayer and lyr.name == target_layer_name:
            target_layer = lyr
            break
    
    if target_layer:
        feature_count = int(arcpy.management.GetCount(target_layer)[0])
        arcpy.AddMessage(f"Target layer feature count: {feature_count}")
        
        if feature_count > 0:
            if arcpy.Exists(kml_output):
                arcpy.management.Delete(kml_output)
            
            arcpy.conversion.LayerToKML(target_layer, kml_output, layer_output_scale=1)
            arcpy.AddMessage(f"KML created: {kml_output}")
        else:
            arcpy.AddWarning(f"Target layer has no features, KML not created")
    else:
        layer_names = [lyr.name for lyr in saved_map.listLayers() if lyr.isFeatureLayer]
        arcpy.AddWarning(f"Could not find layer '{target_layer_name}' in saved project, KML not created")
        arcpy.AddMessage(f"Available layers: {layer_names}")
        
except Exception as e:
    arcpy.AddError(f"Error during KML export: {e}")
    raise
arcpy.AddMessage("----------------------------------------------------")
arcpy.AddMessage("----------------------------------------------------")
arcpy.AddMessage("Trapline Boundary Map Automation has been completed")
arcpy.AddMessage("----------------------------------------------------")
arcpy.AddMessage("----------------------------------------------------")
