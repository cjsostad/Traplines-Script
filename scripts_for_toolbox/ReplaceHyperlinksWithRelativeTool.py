'''
Replace Hyperlinks with Relative Tool Module
Description: Updates absolute hyperlinks in Excel documents to relative paths
Author: Fish and Wildlife Authorizations Geospatial Services, GEOBC
Version: 2.0 - Converted to Python Toolbox tool class format
'''
import arcpy
import openpyxl
import os
import ctypes
from ctypes import wintypes


class ReplaceHyperlinksWithRelativeTool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Replace Hyperlinks with Relative Paths"
        self.description = "Updates absolute hyperlinks in Excel documents to relative paths"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        # Parameter 0: Folder(s) to process
        param0 = arcpy.Parameter(
            displayName="Folder(s) to Process",
            name="folders",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
            multiValue=True)
        
        params = [param0]
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
        folders_param = parameters[0].valueAsText
        
        # MultiValue parameters come as semicolon-separated string
        folders = folders_param.split(';')
        
        # Initialize progress
        arcpy.SetProgressor("default", "Searching for Excel files...")
        
        # Gather all Excel files from the specified folders
        xl_files = []
        arcpy.AddMessage("Gathering Excel files...")
        
        for fld in folders:
            arcpy.AddMessage(f"Searching in: {fld}")
            for root, dirs, files in os.walk(fld):
                for f in files:
                    if f.endswith('.xls') or f.endswith('.xlsx'):
                        xl_files.append(os.path.join(root, f))
        
        if not xl_files:
            arcpy.AddWarning("No Excel files found in the specified folder(s)")
            return
        
        arcpy.AddMessage(f"Found {len(xl_files)} Excel file(s) to process")
        
        # Process each Excel file
        processed_count = 0
        error_count = 0
        
        for xl in xl_files:
            try:
                arcpy.SetProgressorLabel(f"Processing: {os.path.basename(xl)}")
                
                # Get the full UNC path if it's a mapped drive
                xl = self.get_full_path(xl)
                xl_head = os.path.dirname(xl)
                
                # Open the workbook
                arcpy.AddMessage(f"Opening workbook: {os.path.basename(xl)}")
                wb = openpyxl.load_workbook(filename=xl)
                
                replacements_made = 0
                
                # Loop through the sheets within the workbook
                for sheet in wb.worksheets:
                    # Iterate through all cells containing hyperlinks
                    for row in sheet.iter_rows():
                        for cell in row:
                            # Check if the cell is hyperlinked
                            if cell.hyperlink:
                                # Remove the built-in file prefix
                                target = cell.hyperlink.target.replace('file:///', '')
                                
                                # If the hyperlink is to a website, ignore and continue
                                if target.startswith('https://') or target.startswith('http://'):
                                    continue
                                
                                # Get full path for target
                                target = self.get_full_path(target)
                                
                                # Extract the parts of the hyperlink
                                target_head = os.path.dirname(target)
                                target_file = os.path.basename(target)
                                
                                # Find the common directories and return the relative path
                                try:
                                    rel_head = os.path.relpath(target_head, xl_head)
                                except ValueError:
                                    # Different drives - keep absolute path
                                    rel_head = target_head
                                
                                # Set the new target hyperlink to the cell
                                new_target = os.path.join(rel_head, target_file)
                                cell.hyperlink.target = new_target
                                replacements_made += 1
                
                # Save and close the workbook
                if replacements_made > 0:
                    arcpy.AddMessage(f"  Made {replacements_made} replacement(s), saving workbook...")
                    wb.save(xl)
                else:
                    arcpy.AddMessage(f"  No hyperlinks to replace")
                
                wb.close()
                processed_count += 1
                
            except Exception as e:
                arcpy.AddError(f"Error processing {os.path.basename(xl)}: {str(e)}")
                error_count += 1
                continue
        
        # Summary
        arcpy.ResetProgressor()
        arcpy.AddMessage(" ")
        arcpy.AddMessage("===========================================================================")
        arcpy.AddMessage(f"Processing complete:")
        arcpy.AddMessage(f"  Successfully processed: {processed_count} file(s)")
        if error_count > 0:
            arcpy.AddMessage(f"  Errors encountered: {error_count} file(s)")
        arcpy.AddMessage("===========================================================================")
        
        return
    
    def get_full_path(self, str_file):
        """
        Convert mapped drive paths to UNC paths if necessary.
        Returns the full UNC path or the original path if already UNC.
        """
        if not str_file:
            return str_file
        
        # If already a UNC path, return as-is
        if str_file.startswith('\\\\'):
            return str_file
        
        # Try to get the UNC path for mapped drives
        try:
            # Extract drive letter
            if len(str_file) > 1 and str_file[1] == ':':
                drive_letter = str_file[0] + ':'
                
                # Windows API to get UNC path
                remote_name_info = wintypes.DWORD(1)  # REMOTE_NAME_INFO_LEVEL
                buffer_size = wintypes.DWORD(1024)
                buffer = ctypes.create_unicode_buffer(buffer_size.value)
                
                # WNetGetConnection to get UNC path
                result = ctypes.windll.mpr.WNetGetUniversalNameW(
                    str_file,
                    remote_name_info,
                    buffer,
                    ctypes.byref(buffer_size)
                )
                
                if result == 0:  # NO_ERROR
                    # The buffer contains a structure, extract the string
                    return buffer.value
        except:
            pass
        
        # If conversion fails or not a mapped drive, return original
        return str_file
