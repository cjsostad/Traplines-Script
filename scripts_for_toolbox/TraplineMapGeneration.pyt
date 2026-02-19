'''
Trapline Map Generation Python Toolbox
Description: 
This script creates a trapline boundary feature layer and KML by way of user input as GSS Request Number and Trapline Number,
along with any associated Crown Land File(s) with Trapline Cabin features.

Author:  Ozra (Sunny) Rahimi, Evan Breton, Modified by cjsostad
         Ministry of Forests, Lands, Natural Resource Operations
           and Rural Development
      
Usage Note:  This toolbox will work with the Temp_Trapline_Master template in ArcGIS Pro
Version 2.0
'''
import arcpy
import os
import re
from datetime import datetime

# Import additional tool modules
from WildlifeFisheriesSetupTool import WildlifeFisheriesSetupTool
from ReplaceHyperlinksWithRelativeTool import ReplaceHyperlinksWithRelativeTool


# Helper Functions
def get_layer_from_map(map_obj, layer_name):
    """Get a layer from the map with error handling."""
    try:
        layer_list = map_obj.listLayers(layer_name)
        if not layer_list:
            arcpy.AddError(f"ERROR: Layer '{layer_name}' not found in the map.")
            arcpy.AddError("Please check that:")
            arcpy.AddError(f"  1. The layer exists in your map")
            arcpy.AddError(f"  2. The layer name is exactly '{layer_name}' (case-sensitive)")
            arcpy.AddError(f"  3. The layer has not been renamed by a previous run of this tool")
            return None
        return layer_list[0]
    except Exception as e:
        arcpy.AddError(f"ERROR: Failed to access '{layer_name}' layer: {e}")
        return None


def apply_definition_query(layer, query):
    """Apply a definition query to a layer with error handling."""
    try:
        layer.definitionQuery = query
        arcpy.AddMessage(f"Applied filter to {layer.name}: {query}")
        return True
    except Exception as e:
        arcpy.AddWarning(f"Could not apply definition query to {layer.name}: {e}")
        return False


def create_directory(directory):
    """Create a directory if it doesn't exist."""
    if not os.path.exists(directory):
        os.makedirs(directory)
        arcpy.AddMessage(f"Directory created: {directory}")
    else:
        arcpy.AddMessage(f"Directory already exists: {directory}")


def calculate_area_in_hectares(geometry, sq_meters_to_hectares=10000):
    """Calculate area in hectares from geometry."""
    return geometry.area / sq_meters_to_hectares


def update_layer_data_source(layer, shapefile_path, new_name):
    """Update layer data source and rename it."""
    try:
        new_conn_props = layer.connectionProperties
        new_conn_props['connection_info']['database'] = os.path.dirname(shapefile_path)
        new_conn_props['dataset'] = os.path.basename(shapefile_path)
        layer.updateConnectionProperties(layer.connectionProperties, new_conn_props)
        layer.name = new_name
        arcpy.AddMessage(f"Successfully updated layer data source and renamed to: {new_name}")
        return True
    except Exception as e:
        arcpy.AddError(f"Failed to update layer data source: {e}")
        return False


def get_buffered_extent(layer, buffer_percent=0.10):
    """Get the extent of a layer with a buffer percentage."""
    arcpy.SelectLayerByAttribute_management(layer, "NEW_SELECTION", "1=1")
    desc = arcpy.Describe(layer)
    extent = desc.extent
    
    x_buffer = (extent.XMax - extent.XMin) * buffer_percent
    y_buffer = (extent.YMax - extent.YMin) * buffer_percent
    
    extent.XMin -= x_buffer
    extent.XMax += x_buffer
    extent.YMin -= y_buffer
    extent.YMax += y_buffer
    
    arcpy.SelectLayerByAttribute_management(layer, "CLEAR_SELECTION")
    return extent


def round_scale_to_nearest(scale, increment=5000):
    """Round scale up to the nearest increment."""
    return ((int(scale) + increment - 1) // increment) * increment


def export_to_kml(input_feature, output_kml):
    """Export feature to KML with error handling."""
    try:
        if not arcpy.Exists(input_feature):
            arcpy.AddError(f"Feature does not exist: {input_feature}")
            return False
        
        feature_count = int(arcpy.management.GetCount(input_feature)[0])
        arcpy.AddMessage(f"Feature count: {feature_count}")
        
        if feature_count == 0:
            arcpy.AddWarning("Feature has no records, KML not created")
            return False
        
        if arcpy.Exists(output_kml):
            arcpy.management.Delete(output_kml)
        
        temp_layer = "temp_kml_export"
        arcpy.management.MakeFeatureLayer(input_feature, temp_layer)
        arcpy.conversion.LayerToKML(temp_layer, output_kml, layer_output_scale=1)
        arcpy.management.Delete(temp_layer)
        
        arcpy.AddMessage(f"KML created successfully: {output_kml}")
        return True
    except Exception as e:
        arcpy.AddError(f"Error during KML export: {e}")
        return False


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Wildlife Authorization Tools"
        self.alias = "WildlifeTools"

        # List of tool classes associated with this toolbox
        self.tools = [TraplineMapGenerationTool, WildlifeFisheriesSetupTool, ReplaceHyperlinksWithRelativeTool]


class TraplineMapGenerationTool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Generate Trapline Map"
        self.description = "Generates trapline boundary maps, KML, and shapefiles for a given GSS Request and Trapline Number"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        # Parameter 0: GSS Request Number
        param0 = arcpy.Parameter(
            displayName="GSS Request Number",
            name="gss_request_num",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        # Parameter 1: Trapline Number
        param1 = arcpy.Parameter(
            displayName="Trapline Number",
            name="file_num",
            datatype="GPString",
            parameterType="Required",
            direction="Input")
        
        # Parameter 2: Output Folder (Derived)
        param2 = arcpy.Parameter(
            displayName="Output Folder",
            name="output_folder",
            datatype="DEFolder",
            parameterType="Derived",
            direction="Output")
        
        params = [param0, param1, param2]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        
        # Constants
        WORKSPACE_BASE = r'\\spatialfiles.bcgov\srm\gss\authorizations\wildlife'
        MAP_NAME = 'Map'
        LAYOUT_NAME = 'Layout'
        DEFAULT_SCALE = 250000
        AREA_FIELD = "Area_ha"
        CROWN_LAND_FIELD = "CROWN_LAND"
        TRAPLINE_FIELD = "TRAPLINE_AREA_IDENTIFIER"
        SQ_METERS_TO_HECTARES = 10000

        # Get parameters
        gss_request_num = parameters[0].valueAsText
        file_num = parameters[1].valueAsText
        
        # Initialize progress bar (7 steps total)
        arcpy.SetProgressor("step", "Processing trapline map...", 0, 7, 1)
        
        # Validate inputs
        if not gss_request_num:
            arcpy.AddError("ERROR: No GSS Request Number provided. Please provide a valid GSS Request Number.")
            return
        
        if not file_num:
            arcpy.AddError("ERROR: No trapline boundary number provided. Please provide a valid file number.")
            return
        
        # Create or get the feature_layer object from ArcGIS Pro's content pane
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
        try:
            map_obj = aprx.listMaps(MAP_NAME)[0]
        except (IndexError, KeyError):
            arcpy.AddError(f"ERROR: Could not find map named '{MAP_NAME}' in the current project. Please check your map name.")
            return
        except Exception as e:
            arcpy.AddError(f"ERROR: Failed to access map: {e}")
            return
        
        try:
            layout = aprx.listLayouts(LAYOUT_NAME)[0]
        except (IndexError, KeyError):
            arcpy.AddError(f"ERROR: Could not find layout named '{LAYOUT_NAME}' in the current project. Please check your layout name.")
            return
        except Exception as e:
            arcpy.AddError(f"ERROR: Failed to access layout: {e}")
            return
        
        # Get layer objects
        all_trapline_boundaries_obj = get_layer_from_map(map_obj, "All Trapline Boundaries")
        if not all_trapline_boundaries_obj:
            return
        
        all_trapline_cabins_obj = get_layer_from_map(map_obj, "All Trapline Cabins")
        if not all_trapline_cabins_obj:
            return
        
        # Apply definition query to cabin layer
        cabin_filter = "TENURE_SUBPURPOSE = 'TRAPLINE CABIN'"
        apply_definition_query(all_trapline_cabins_obj, cabin_filter)
        
        ################################################################################################################################
        #
        # Step 1 - Create Folder Structure
        #
        ################################################################################################################################
        arcpy.SetProgressorLabel("Step 1 of 7: Creating folder structure...")
        
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
        
        # Add clickable link to open the output directory
        arcpy.AddMessage(f"<a href='file:///{gss_request_dir}'>Click here to open output folder</a>")
        arcpy.SetProgressorPosition()
        
        ################################################################################################################################
        #
        # Step 2 - Query and Export Trapline Boundary
        #
        #############################################################################################################################
        arcpy.SetProgressorLabel("Step 2 of 7: Querying trapline boundary from BCGW...")
        arcpy.AddMessage("Step 2 - Querying Trapline Boundary from BCGW")
        
        # Create a temporary layer with definition query (don't modify the original BCGW layer)
        temp_query_layer = "temp_trapline_query"
        arcpy.management.MakeFeatureLayer(all_trapline_boundaries_obj, temp_query_layer)
        
        # Build simple expression that works with BCGW feature services
        expression = f"{TRAPLINE_FIELD} = '{file_num}'"
        arcpy.AddMessage(f"Using expression: {expression}")
        
        # Set the definition query on the temporary layer
        arcpy.management.SelectLayerByAttribute(temp_query_layer, "NEW_SELECTION", expression)
        
        # Error Handling - Check if any records were found
        count = int(arcpy.management.GetCount(temp_query_layer)[0])
        
        if count == 0:
            arcpy.AddError(f"ERROR: No records returned for trapline {file_num}. Please check the file number and try again.")
            if arcpy.Exists(temp_query_layer):
                arcpy.management.Delete(temp_query_layer)
            return
        else:
            arcpy.AddMessage(f"         Found {count} record(s) for trapline {file_num}")
        
        arcpy.SetProgressorPosition()

        # Specify the output file path for the exported feature
        application_trapline_boundary = os.path.join(shapefile_dir, f'{file_num}.shp')
        arcpy.AddMessage(f"Output feature path: {application_trapline_boundary}")
        
        ###########################################################################################################################################
        #
        # Step 3 - Export the Feature to a Shapefile
        #
        ###########################################################################################################################################
        arcpy.SetProgressorLabel("Step 3 of 7: Exporting to shapefile...")
        arcpy.AddMessage("Step 3 - Exporting to shapefile")
        try:
            arcpy.management.CopyFeatures(temp_query_layer, application_trapline_boundary)
            arcpy.AddMessage(f"Shapefile created: {application_trapline_boundary}")
        except arcpy.ExecuteError as e:
            arcpy.AddError(f"CopyFeatures error: {e}")
            if arcpy.Exists(temp_query_layer):
                arcpy.management.Delete(temp_query_layer)
            return
        
        # Clean up temporary query layer
        if arcpy.Exists(temp_query_layer):
            arcpy.management.Delete(temp_query_layer)
        
        # Add a new field for the area in hectares if it doesn't already exist
        if AREA_FIELD not in [f.name for f in arcpy.ListFields(application_trapline_boundary)]:
            arcpy.management.AddField(application_trapline_boundary, AREA_FIELD, "DOUBLE")
            arcpy.AddMessage(f"Field '{AREA_FIELD}' added to the feature class.")
        
        # Calculate the area for each polygon and update the new field
        arcpy.AddMessage("Calculating area in hectares...")
        formatted_area = ""
        with arcpy.da.UpdateCursor(application_trapline_boundary, ["SHAPE@", AREA_FIELD]) as cursor:
            for row in cursor:
                area_hectares = calculate_area_in_hectares(row[0], SQ_METERS_TO_HECTARES)
                row[1] = area_hectares
                cursor.updateRow(row)
                formatted_area = f"{area_hectares:.2f} ha."
                arcpy.AddMessage(f"Formatted area: {formatted_area}")
        arcpy.AddMessage(f"Area in hectares has been added to the field '{AREA_FIELD}'.")
        
        arcpy.SetProgressorPosition()
        
        ##############################################################################################################
        #
        # Step 4 - Clip and Export Trapline Cabins
        #
        ##############################################################################################################
        arcpy.SetProgressorLabel("Step 4 of 7: Clipping trapline cabins...")
        arcpy.AddMessage("Step 4 - Clipping Trapline Cabins layer")
        clipped_cabins_output = os.path.join(shapefile_dir, f'{file_num}_Cabins.shp')
        arcpy.AddMessage(f"Output feature path: {clipped_cabins_output}")

        # Clip the "Trapline Cabins" layer based on the feature layer (use layer object, not string name)
        arcpy.analysis.Clip(all_trapline_cabins_obj, application_trapline_boundary, clipped_cabins_output)
        arcpy.AddMessage(f"Clipping of trapline cabins completed.")

        # Initialize Crown_Num_Values to handle cases where field doesn't exist
        Crown_Num_Values = []
        Crown_Num_Values_String = ""
        
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
            
            # Remove duplicates and sort
            Crown_Num_Values = sorted(list(set(Crown_Num_Values)))
            
            if Crown_Num_Values:
                Crown_Num_Values_String = "_".join(map(str, Crown_Num_Values))
                arcpy.AddMessage(f"Found Crown Land values: {Crown_Num_Values_String}")
        
        ##############################################################################################################
        #
        # Step 4a - Replace Data Source for Existing Trapline Cabin Layer
        #
        ##############################################################################################################
        arcpy.SetProgressorLabel("Step 4a of 7: Replacing cabin data source...")
        arcpy.AddMessage("Step 4a - Replacing data source for existing trapline cabin layer")
        
        # Find layer that starts with "Trapline Cabin" or "Trapline_Cabin_"
        cabin_target_layer = None
        
        for lyr in map_obj.listLayers():
            if lyr.isFeatureLayer and (lyr.name.startswith("Trapline Cabin") or lyr.name.startswith("Trapline_Cabin_")):
                cabin_target_layer = lyr
                arcpy.AddMessage(f"Found target cabin layer: {lyr.name}")
                break
        
        if cabin_target_layer is None:
            arcpy.AddWarning("WARNING: Could not find a layer starting with 'Trapline Cabin' or 'Trapline_Cabin_'.")
            arcpy.AddWarning("Please ensure you have a trapline cabin layer in your map to update.")
            arcpy.AddWarning("Continuing without updating cabin layer data source...")
        else:
            # Rename the layer based on Crown Land values
            if Crown_Num_Values_String:
                new_cabin_layer_name = f"Trapline_Cabin_{Crown_Num_Values_String}"
            else:
                new_cabin_layer_name = f"Trapline_Cabin_{file_num}"
            
            update_layer_data_source(cabin_target_layer, clipped_cabins_output, new_cabin_layer_name)
        
        ##############################################################################################################
        #
        # Step 4b - Replace Data Source for Existing Trapline Layer
        #
        ##############################################################################################################
        arcpy.SetProgressorLabel("Step 4b of 7: Replacing boundary data source...")
        arcpy.AddMessage("Step 4b - Replacing data source for existing trapline layer")
        
        # Find layer that starts with "TR" (e.g., TR0440T001, TR0430T001, etc.)
        target_layer = None
        
        for lyr in map_obj.listLayers():
            if lyr.isFeatureLayer and lyr.name.startswith("TR"):
                target_layer = lyr
                arcpy.AddMessage(f"Found target layer: {lyr.name}")
                break
        
        if target_layer is None:
            arcpy.AddWarning("WARNING: Could not find a layer starting with 'TR'.")
            arcpy.AddWarning("Please ensure you have a trapline layer in your map to update.")
            arcpy.AddWarning("Continuing without updating layer data source...")
        else:
            new_layer_name = f"{file_num} ({formatted_area})"
            update_layer_data_source(target_layer, application_trapline_boundary, new_layer_name)
        
        # Create a new variable for Crown cabins string (for further operations if needed)
        new_crown_cabins_str = f"{file_num}_Cabins_{Crown_Num_Values_String}" if Crown_Num_Values else "Trapline_Cabin_No_Values"
        arcpy.AddMessage(f"New Crown cabins variable: {new_crown_cabins_str} created.")
        
        arcpy.SetProgressorPosition()

        # Update map title text element
        for elm in layout.listElements("TEXT_ELEMENT"):
            if elm.name == "Map Title":
                elm.text = f"Trapline {file_num}"
                arcpy.AddMessage("Map title text element updated")
                break
        
        # Zoom to trapline boundary feature and set scale
        arcpy.SetProgressorLabel("Step 5 of 7: Zooming to feature and setting scale...")
        arcpy.AddMessage("Step 5 - Zooming to feature and setting scale")
        
        # Use the updated target layer if found, otherwise skip zoom
        if target_layer is not None:
            zoom_feature_layer = target_layer
        else:
            # Fallback: create a temporary layer from the shapefile for zooming
            arcpy.AddMessage("Creating temporary layer for zoom...")
            zoom_feature_layer = "temp_zoom_layer"
            arcpy.management.MakeFeatureLayer(application_trapline_boundary, zoom_feature_layer)
        
        mapframe = layout.listElements('MAPFRAME_ELEMENT', 'Map Frame')[0]

        # Get buffered extent and set camera
        extent = get_buffered_extent(zoom_feature_layer, buffer_percent=0.10)
        mapframe.camera.setExtent(extent)
        
        # Clean up temporary zoom layer if created
        if target_layer is None and arcpy.Exists("temp_zoom_layer"):
            arcpy.management.Delete("temp_zoom_layer")

        # Round scale up to nearest 5000
        rounded_scale = round_scale_to_nearest(mapframe.camera.scale, increment=5000)
        mapframe.camera.scale = rounded_scale
        arcpy.AddMessage(f"Zoomed to trapline boundary and set scale to: {rounded_scale}")
        
        arcpy.SetProgressorPosition()
        
        ##############################################################################################################
        #
        # Step 6 - Export PDF and save project
        #
        ##############################################################################################################
        arcpy.SetProgressorLabel("Step 6 of 7: Exporting PDF and saving project...")
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
            return

        # Save project copy
        aprx_path = os.path.join(maps_dir, f"{file_num}.aprx")
        try:
            aprx.saveACopy(aprx_path)
            arcpy.AddMessage(f"ArcGIS Pro project saved: {aprx_path}")
        except Exception as e:
            arcpy.AddError(f"Failed to save project: {e}")
            return
        
        arcpy.SetProgressorPosition()
        
        ##############################################################################################################
        #
        # Step 7 - Export KML
        #
        ##############################################################################################################
        arcpy.SetProgressorLabel("Step 7 of 7: Exporting KML...")
        arcpy.AddMessage("Step 7 - Exporting KML")

        kml_output = os.path.join(kml_dir, f"{file_num}.kmz")
        export_to_kml(application_trapline_boundary, kml_output)
        
        arcpy.SetProgressorPosition()
        arcpy.ResetProgressor()
        
        arcpy.AddMessage("----------------------------------------------------")
        arcpy.AddMessage("----------------------------------------------------")
        arcpy.AddMessage("Trapline Boundary Map Automation has been completed")
        arcpy.AddMessage("----------------------------------------------------")
        arcpy.AddMessage("----------------------------------------------------")
        arcpy.AddMessage(f"<a href='file:///{gss_request_dir}'>Click here to open output folder</a>")
        
        # Set the derived output parameter
        parameters[2].value = gss_request_dir
        
        return
