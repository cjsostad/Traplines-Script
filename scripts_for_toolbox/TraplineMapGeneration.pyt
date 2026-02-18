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


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the .pyt file)."""
        self.label = "Trapline Map Generation Toolbox"
        self.alias = "TraplineTools"

        # List of tool classes associated with this toolbox
        self.tools = [TraplineMapGenerationTool]


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
        
        params = [param0, param1]
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
        
        # Get layer objects with specific error handling
        try:
            trapline_boundaries_list = map_obj.listLayers("All Trapline Boundaries")
            if not trapline_boundaries_list:
                arcpy.AddError("ERROR: Layer 'All Trapline Boundaries' not found in the map.")
                arcpy.AddError("Please check that:")
                arcpy.AddError("  1. The layer exists in your map")
                arcpy.AddError("  2. The layer name is exactly 'All Trapline Boundaries' (case-sensitive)")
                arcpy.AddError("  3. The layer has not been renamed by a previous run of this tool")
                return
            all_trapline_boundaries_obj = trapline_boundaries_list[0]
        except Exception as e:
            arcpy.AddError(f"ERROR: Failed to access 'All Trapline Boundaries' layer: {e}")
            return
        
        try:
            trapline_cabins_list = map_obj.listLayers("All Trapline Cabins")
            if not trapline_cabins_list:
                arcpy.AddError("ERROR: Layer 'All Trapline Cabins' not found in the map.")
                arcpy.AddError("Please check that:")
                arcpy.AddError("  1. The layer exists in your map")
                arcpy.AddError("  2. The layer name is exactly 'All Trapline Cabins' (case-sensitive)")
                arcpy.AddError("  3. The layer has not been renamed by a previous run of this tool")
                return
            all_trapline_cabins_obj = trapline_cabins_list[0]
        except Exception as e:
            arcpy.AddError(f"ERROR: Failed to access 'All Trapline Cabins' layer: {e}")
            return
        
        # Apply permanent definition query to All Trapline Cabins BCGW layer
        try:
            cabin_filter = "TENURE_SUBPURPOSE = 'TRAPLINE CABIN'"
            all_trapline_cabins_obj.definitionQuery = cabin_filter
            arcpy.AddMessage(f"Applied filter to All Trapline Cabins: {cabin_filter}")
        except Exception as e:
            arcpy.AddWarning(f"Could not apply definition query to All Trapline Cabins: {e}")
        
        # Function to create a directory if it doesn't exist
        def create_directory(directory):
            if not os.path.exists(directory):
                os.makedirs(directory)
                arcpy.AddMessage(f"Directory created: {directory}")
            else:
                arcpy.AddMessage(f"Directory already exists: {directory}")

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
        # Step 2 - Query and Export Trapline Boundary
        #
        #############################################################################################################################
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

        # Specify the output file path for the exported feature
        application_trapline_boundary = os.path.join(shapefile_dir, f'{file_num}.shp')
        arcpy.AddMessage(f"Output feature path: {application_trapline_boundary}")
        
        ###########################################################################################################################################
        #
        # Step 3 - Export the Feature to a Shapefile
        #
        ###########################################################################################################################################
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
        # Step 4 - Clip and Export Trapline Cabins
        #
        ##############################################################################################################
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
            try:
                # Get connection properties from the shapefile
                new_conn_props = cabin_target_layer.connectionProperties
                new_conn_props['connection_info']['database'] = os.path.dirname(clipped_cabins_output)
                new_conn_props['dataset'] = os.path.basename(clipped_cabins_output)
                
                # Update the connection properties
                cabin_target_layer.updateConnectionProperties(cabin_target_layer.connectionProperties, new_conn_props)
                
                # Rename the layer based on Crown Land values
                if Crown_Num_Values_String:
                    new_cabin_layer_name = f"Trapline_Cabin_{Crown_Num_Values_String}"
                else:
                    new_cabin_layer_name = f"Trapline_Cabin_{file_num}"
                
                cabin_target_layer.name = new_cabin_layer_name
                arcpy.AddMessage(f"Successfully updated cabin layer data source and renamed to: {new_cabin_layer_name}")
                
            except Exception as e:
                arcpy.AddError(f"Failed to update cabin layer data source: {e}")
                arcpy.AddError("Please check that the layer exists and is a valid feature layer.")
        
        ##############################################################################################################
        #
        # Step 4b - Replace Data Source for Existing Trapline Layer
        #
        ##############################################################################################################
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
            try:
                # Get connection properties from the shapefile
                new_conn_props = target_layer.connectionProperties
                new_conn_props['connection_info']['database'] = os.path.dirname(application_trapline_boundary)
                new_conn_props['dataset'] = os.path.basename(application_trapline_boundary)
                
                # Update the connection properties
                target_layer.updateConnectionProperties(target_layer.connectionProperties, new_conn_props)
                
                # Rename the layer
                new_layer_name = f"{file_num} ({formatted_area})"
                target_layer.name = new_layer_name
                arcpy.AddMessage(f"Successfully updated layer data source and renamed to: {new_layer_name}")
                
            except Exception as e:
                arcpy.AddError(f"Failed to update layer data source: {e}")
                arcpy.AddError("Please check that the layer exists and is a valid feature layer.")
        
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
        
        # Use the updated target layer if found, otherwise skip zoom
        if target_layer is not None:
            zoom_feature_layer = target_layer
        else:
            # Fallback: create a temporary layer from the shapefile for zooming
            arcpy.AddMessage("Creating temporary layer for zoom...")
            zoom_feature_layer = "temp_zoom_layer"
            arcpy.management.MakeFeatureLayer(application_trapline_boundary, zoom_feature_layer)
        
        mapframe = layout.listElements('MAPFRAME_ELEMENT', 'Map Frame')[0]

        # Select all features and zoom
        arcpy.SelectLayerByAttribute_management(zoom_feature_layer, "NEW_SELECTION", "1=1")
        mapframe.zoomToAllLayers(True)
        arcpy.SelectLayerByAttribute_management(zoom_feature_layer, "CLEAR_SELECTION")
        
        # Clean up temporary zoom layer if created
        if target_layer is None and arcpy.Exists("temp_zoom_layer"):
            arcpy.management.Delete("temp_zoom_layer")

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
            return

        # Save project copy
        aprx_path = os.path.join(maps_dir, f"{file_num}.aprx")
        try:
            aprx.saveACopy(aprx_path)
            arcpy.AddMessage(f"ArcGIS Pro project saved: {aprx_path}")
        except Exception as e:
            arcpy.AddError(f"Failed to save project: {e}")
            return
        
        ##############################################################################################################
        #
        # Step 7 - Export KML
        #
        ##############################################################################################################
        arcpy.AddMessage("Step 7 - Exporting KML")

        kml_output = os.path.join(kml_dir, f"{file_num}.kmz")

        # Export KML using the shapefile directly instead of layer reference
        try:
            # Check if shapefile exists and has features
            if arcpy.Exists(application_trapline_boundary):
                feature_count = int(arcpy.management.GetCount(application_trapline_boundary)[0])
                arcpy.AddMessage(f"Shapefile feature count: {feature_count}")
                
                if feature_count > 0:
                    # Delete existing KML if it exists
                    if arcpy.Exists(kml_output):
                        arcpy.management.Delete(kml_output)
                    
                    # Create a temporary layer from the shapefile for KML conversion
                    temp_kml_layer = "temp_kml_layer"
                    arcpy.management.MakeFeatureLayer(application_trapline_boundary, temp_kml_layer)
                    
                    # Export to KML
                    arcpy.conversion.LayerToKML(temp_kml_layer, kml_output, layer_output_scale=1)
                    arcpy.AddMessage(f"KML created successfully: {kml_output}")
                    
                    # Clean up temporary layer
                    if arcpy.Exists(temp_kml_layer):
                        arcpy.management.Delete(temp_kml_layer)
                else:
                    arcpy.AddWarning(f"Shapefile has no features, KML not created")
            else:
                arcpy.AddError(f"Shapefile does not exist: {application_trapline_boundary}")
                
        except arcpy.ExecuteError as e:
            arcpy.AddError(f"ArcPy error during KML export: {e}")
            arcpy.AddError(arcpy.GetMessages())
        except Exception as e:
            arcpy.AddError(f"Error during KML export: {e}")
        
        arcpy.AddMessage("----------------------------------------------------")
        arcpy.AddMessage("----------------------------------------------------")
        arcpy.AddMessage("Trapline Boundary Map Automation has been completed")
        arcpy.AddMessage("----------------------------------------------------")
        arcpy.AddMessage("----------------------------------------------------")
        
        return
