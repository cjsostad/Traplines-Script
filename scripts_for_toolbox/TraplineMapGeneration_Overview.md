# **Trapline Map Generation Script - Overview**

## **Purpose:**
Automates the creation of trapline maps by querying BCGW data, creating shapefiles, updating map layers, and producing PDF/KML outputs - all while preserving layer symbology through data source replacement.

---

## **Initial Setup:**

**Dynamic Workspace Creation:**
- Determines current year automatically
- Creates folder structure: `wildlife\{year}\traplines\{GSS_Request_Number}\`
- Subfolders: `kml`, `shapefile`, `maps`

**BCGW Layer Connections:**
- Locates "All Trapline Boundaries" layer (connected to BCGW)
- Locates "All Trapline Cabins" layer (connected to BCGW)
- Applies Def Query filter to cabins: `TENURE_SUBPURPOSE = 'TRAPLINE CABIN'`
- Both BCGW layers remain unchanged throughout script execution

---

## **Step 2-3: Trapline Boundary Processing**

**Query BCGW:**
- Creates temporary layer from "All Trapline Boundaries"
- Selects features matching user's trapline number via `TRAPLINE_AREA_IDENTIFIER` field
- Validates that records exist (error if not found)

**Export to Shapefile:**
- Copies selected feature to local shapefile: `{trapline_num}.shp`
- Stored in shapefile directory under GSS request folder

**Area Calculation:**
- Adds `Area_ha` field to shapefile
- Calculates area in hectares from polygon geometry (converts from square meters)
- Formats as text: "XXXXX.XX ha."

---

## **Step 4-4a: Trapline Cabins Processing**

**Spatial Clip Operation:**
- Uses trapline boundary shapefile as clip feature
- Clips all cabin features from BCGW "All Trapline Cabins" layer
- Output: `{trapline_num}_Cabins.shp` with all cabins inside boundary

**Crown Land Attribution:**
- Reads `CROWN_LAND` field from each clipped cabin feature
- Collects all unique Crown Land file numbers
- Sorts and deduplicates values (e.g., CL123, CL456, CL789)

**Replace Cabin Layer Data Source:**
- Searches map for existing layer starting with "Trapline Cabin" or "Trapline_Cabin_"
- Updates that layer's connection to point to new clipped shapefile
- Renames layer: `Trapline_Cabin_{Crown_Land_Values}` (preserves symbology)
- If no cabins found, uses trapline number as fallback name

---

## **Step 4b: Trapline Boundary Layer Update**

**Replace Boundary Layer Data Source:**
- Searches map for existing layer starting with "TR"
- Updates that layer's connection to point to new boundary shapefile
- Renames layer: `{trapline_num} ({area_ha})` (e.g., "TR0401T005 (16100.83 ha.)")
- Preserves all symbology, labels, and layer properties

---

## **Step 5: Map Navigation**

**Update Map Title:**
- Finds text element named "Map Title" in layout
- Updates text to: `Trapline {trapline_num}`

**Zoom and Scale:**
- Selects all features in updated trapline boundary layer
- Zooms map frame to selected features
- Sets fixed scale to 1:250,000
- Clears selection

---

## **Step 6: PDF Export**

**Layout Export:**
- Generates filename: `Trapline_{trapline_num}_{YYYYMMDD}.pdf`
- Exports current layout at 300 DPI with best image quality
- Saves to maps directory
- Uses vector compression for smaller file size

**Project Save:**
- Saves copy of ArcGIS Pro project: `{trapline_num}.aprx`
- Saved to maps directory for future reference/editing

---

## **Step 7: KML Export**

**KML Generation:**
- Creates temporary feature layer from boundary shapefile
- Validates feature count
- Converts to KMZ format for use in Google Earth
- Output: `{trapline_num}.kmz` in kml directory
- Cleans up temporary layers

---

## **Key GIS Concepts Used:**

1. **Definition Queries** - Filter BCGW layers without modifying source data
2. **Spatial Clip** - Extract features within boundary polygon
3. **Data Source Replacement** - Update layer connections while preserving symbology
4. **Geometry Calculations** - Calculate area from polygon geometry
5. **Map Automation** - Programmatic zoom, scale setting, and element updates
6. **Multi-format Export** - PDF for printing, KMZ for web/mobile viewing
7. **Workspace Management** - Organized output structure for multiple requests

---

## **Benefits of This Approach:**

- **BCGW layers unchanged** - Can run repeatedly without breaking connections
- **Symbology preserved** - Layers maintain their visual styling
- **Automated organization** - Each GSS request gets its own folder
- **Date-stamped outputs** - Easy version tracking
- **Multiple formats** - PDF for distribution, KMZ for field use, shapefiles for GIS work

---

## **User Inputs Required:**

1. **GSS Request Number** - Used to organize outputs into request-specific folders
2. **Trapline Number** - Used to query BCGW and name output files (format: TR0XXXXXNNN)

---

## **Output Files Generated:**

```
wildlife\{year}\traplines\{GSS_Request_Number}\
├── shapefile\
│   ├── {trapline_num}.shp (+ associated files)
│   └── {trapline_num}_Cabins.shp (+ associated files)
├── maps\
│   ├── Trapline_{trapline_num}_{YYYYMMDD}.pdf
│   └── {trapline_num}.aprx
└── kml\
    └── {trapline_num}.kmz
```
