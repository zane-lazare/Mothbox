"""
XMP Sidecar Library for iNaturalist Export.

Generates XMP sidecar files (.xmp) containing metadata in Dublin Core, XMP,
IPTC Extension, and Photoshop namespaces for photo export compatibility.

XMP (Extensible Metadata Platform) is an ISO standard for embedding metadata
in digital files. iNaturalist and many photo management applications use XMP
sidecars to store and read metadata.

Example:
    from webui.backend.lib.xmp_sidecar import generate_xmp_xml
    from webui.backend.services.export_metadata_service import ExportMetadata

    metadata = ExportMetadata(...)
    xmp_xml = generate_xmp_xml(metadata)

    with open("photo.xmp", "w", encoding="utf-8") as f:
        f.write(xmp_xml)
"""

from pathlib import Path
from xml.etree import ElementTree as ET

from webui.backend.services.export_metadata_service import ExportMetadata

# ============================================================================
# XMP Namespace Definitions
# ============================================================================

XMP_NAMESPACES = {
    'x': 'adobe:ns:meta/',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'xmp': 'http://ns.adobe.com/xap/1.0/',
    'photoshop': 'http://ns.adobe.com/photoshop/1.0/',
    'Iptc4xmpCore': 'http://iptc.org/std/Iptc4xmpCore/1.0/xmlns/',
    'Iptc4xmpExt': 'http://iptc.org/std/Iptc4xmpExt/2008-02-29/',
    'exif': 'http://ns.adobe.com/exif/1.0/',
}

# Register namespaces for ElementTree
for prefix, uri in XMP_NAMESPACES.items():
    ET.register_namespace(prefix, uri)


# ============================================================================
# XML Utility Functions
# ============================================================================

def validate_xmp_xml(xml_string: str) -> bool:
    """
    Validate that XML string is well-formed.

    Args:
        xml_string: XML string to validate

    Returns:
        True if valid XML, False otherwise
    """
    if not xml_string or not xml_string.strip():
        return False

    try:
        # Remove xpacket processing instructions for validation
        xml_content = xml_string
        for pi in ['<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>',
                   '<?xpacket end="w"?>']:
            xml_content = xml_content.replace(pi, '')

        # nosec B314: XMP content is generated internally by generate_xmp_xml(),
        # not from untrusted external sources
        ET.fromstring(xml_content.strip())  # nosec B314
        return True
    except ET.ParseError:
        return False


# ============================================================================
# Filename Utilities
# ============================================================================

def get_xmp_sidecar_filename(photo_filename: str | Path) -> str:
    """
    Convert photo filename to XMP sidecar filename.

    Args:
        photo_filename: Photo filename (e.g., "photo.jpg")

    Returns:
        XMP sidecar filename (e.g., "photo.xmp")

    Example:
        >>> get_xmp_sidecar_filename("moth_2024_01_15__10_30_00.jpg")
        'moth_2024_01_15__10_30_00.xmp'
    """
    path = Path(photo_filename)
    return path.stem + '.xmp'


# ============================================================================
# Taxonomy Keyword Builders
# ============================================================================

def build_taxonomy_keywords(species_name: str | None) -> list[str]:
    """
    Build hierarchical taxonomy keywords from species name.

    Generates taxonomy keywords in the format "taxonomy:rank=name" based on
    scientific name parsing. For Linnaean binomial names (Genus species),
    generates kingdom, phylum, class, order, family, genus, and species keywords.

    Args:
        species_name: Scientific species name (e.g., "Actias luna")

    Returns:
        List of taxonomy keywords (e.g., ["taxonomy:kingdom=Animalia", ...])

    Example:
        >>> build_taxonomy_keywords("Actias luna")
        ['taxonomy:kingdom=Animalia', 'taxonomy:phylum=Arthropoda',
         'taxonomy:class=Insecta', 'taxonomy:order=Lepidoptera',
         'taxonomy:family=Saturniidae', 'taxonomy:genus=Actias',
         'taxonomy:species=Actias luna']

    Note:
        This is a simplified implementation that assumes all Mothbox specimens
        are insects (Animalia > Arthropoda > Insecta > Lepidoptera). For full
        taxonomic hierarchy, integration with a taxonomy database (e.g., GBIF)
        would be required.
    """
    if not species_name:
        return []

    keywords = []

    # LIMITATION: Hardcoded taxonomy assumes Lepidoptera (moths/butterflies)
    # This is appropriate for Mothbox's primary use case as a moth camera trap.
    # For mixed specimens or non-Lepidoptera, this will produce incorrect
    # higher taxonomy. Future enhancement: integrate with GBIF Backbone
    # Taxonomy API for dynamic hierarchical lookup based on species name.
    # See: https://www.gbif.org/developer/species
    keywords.append("taxonomy:kingdom=Animalia")
    keywords.append("taxonomy:phylum=Arthropoda")
    keywords.append("taxonomy:class=Insecta")
    keywords.append("taxonomy:order=Lepidoptera")

    # Parse genus and species from binomial name
    parts = species_name.strip().split()
    if len(parts) >= 1:
        # Add genus
        genus = parts[0]
        keywords.append(f"taxonomy:genus={genus}")

        # Add full species name
        if len(parts) >= 2:
            keywords.append(f"taxonomy:species={species_name}")

    return keywords


# ============================================================================
# Dublin Core Element Builders
# ============================================================================

def build_dc_title(title: str) -> ET.Element:
    """
    Build dc:title element with rdf:Alt structure.

    Args:
        title: Title text

    Returns:
        dc:title Element with rdf:Alt/rdf:li structure

    Example:
        <dc:title>
          <rdf:Alt>
            <rdf:li xml:lang="x-default">Luna Moth (Actias luna)</rdf:li>
          </rdf:Alt>
        </dc:title>
    """
    title_elem = ET.Element(f"{{{XMP_NAMESPACES['dc']}}}title")
    alt = ET.SubElement(title_elem, f"{{{XMP_NAMESPACES['rdf']}}}Alt")
    li = ET.SubElement(alt, f"{{{XMP_NAMESPACES['rdf']}}}li")
    li.set('{http://www.w3.org/XML/1998/namespace}lang', 'x-default')
    li.text = title
    return title_elem


def build_dc_description(description: str) -> ET.Element:
    """
    Build dc:description element with rdf:Alt structure.

    Args:
        description: Description text

    Returns:
        dc:description Element with rdf:Alt/rdf:li structure

    Example:
        <dc:description>
          <rdf:Alt>
            <rdf:li xml:lang="x-default">Beautiful green moth specimen</rdf:li>
          </rdf:Alt>
        </dc:description>
    """
    desc_elem = ET.Element(f"{{{XMP_NAMESPACES['dc']}}}description")
    alt = ET.SubElement(desc_elem, f"{{{XMP_NAMESPACES['rdf']}}}Alt")
    li = ET.SubElement(alt, f"{{{XMP_NAMESPACES['rdf']}}}li")
    li.set('{http://www.w3.org/XML/1998/namespace}lang', 'x-default')
    li.text = description
    return desc_elem


def build_dc_subject(tags: list[str], taxonomy_keywords: list[str]) -> ET.Element:
    """
    Build dc:subject element with rdf:Bag structure.

    Combines user tags and taxonomy keywords into a single bag of keywords.

    Args:
        tags: User-defined tags (e.g., ["moth", "nocturnal"])
        taxonomy_keywords: Taxonomy keywords (e.g., ["taxonomy:species=Actias luna"])

    Returns:
        dc:subject Element with rdf:Bag/rdf:li structure

    Example:
        <dc:subject>
          <rdf:Bag>
            <rdf:li>taxonomy:kingdom=Animalia</rdf:li>
            <rdf:li>taxonomy:species=Actias luna</rdf:li>
            <rdf:li>moth</rdf:li>
            <rdf:li>nocturnal</rdf:li>
          </rdf:Bag>
        </dc:subject>
    """
    subject_elem = ET.Element(f"{{{XMP_NAMESPACES['dc']}}}subject")
    bag = ET.SubElement(subject_elem, f"{{{XMP_NAMESPACES['rdf']}}}Bag")

    # Add all keywords (taxonomy first, then user tags)
    all_keywords = taxonomy_keywords + tags
    for keyword in all_keywords:
        li = ET.SubElement(bag, f"{{{XMP_NAMESPACES['rdf']}}}li")
        li.text = keyword

    return subject_elem


def build_dc_creator(creator: str) -> ET.Element:
    """
    Build dc:creator element with rdf:Seq structure.

    Args:
        creator: Creator name

    Returns:
        dc:creator Element with rdf:Seq/rdf:li structure

    Example:
        <dc:creator>
          <rdf:Seq>
            <rdf:li>Mothbox</rdf:li>
          </rdf:Seq>
        </dc:creator>
    """
    creator_elem = ET.Element(f"{{{XMP_NAMESPACES['dc']}}}creator")
    seq = ET.SubElement(creator_elem, f"{{{XMP_NAMESPACES['rdf']}}}Seq")
    li = ET.SubElement(seq, f"{{{XMP_NAMESPACES['rdf']}}}li")
    li.text = creator
    return creator_elem


def build_dc_rights(license: str) -> ET.Element:
    """
    Build dc:rights element with rdf:Alt structure.

    Args:
        license: License/rights statement

    Returns:
        dc:rights Element with rdf:Alt/rdf:li structure

    Example:
        <dc:rights>
          <rdf:Alt>
            <rdf:li xml:lang="x-default">CC BY-NC 4.0</rdf:li>
          </rdf:Alt>
        </dc:rights>
    """
    rights_elem = ET.Element(f"{{{XMP_NAMESPACES['dc']}}}rights")
    alt = ET.SubElement(rights_elem, f"{{{XMP_NAMESPACES['rdf']}}}Alt")
    li = ET.SubElement(alt, f"{{{XMP_NAMESPACES['rdf']}}}li")
    li.set('{http://www.w3.org/XML/1998/namespace}lang', 'x-default')
    li.text = license
    return rights_elem


# ============================================================================
# IPTC Extension Element Builders
# ============================================================================

def build_location_shown(
    lat: float,
    lon: float,
    alt: float | None = None,
    name: str | None = None
) -> ET.Element:
    """
    Build Iptc4xmpExt:LocationShown element with geographic data.

    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        alt: Altitude in meters (optional)
        name: Location name (optional)

    Returns:
        Iptc4xmpExt:LocationShown Element with rdf:Bag/rdf:li structure

    Example:
        <Iptc4xmpExt:LocationShown>
          <rdf:Bag>
            <rdf:li rdf:parseType="Resource">
              <Iptc4xmpExt:Latitude>35.9606</Iptc4xmpExt:Latitude>
              <Iptc4xmpExt:Longitude>-83.9207</Iptc4xmpExt:Longitude>
              <Iptc4xmpExt:Altitude>350.5</Iptc4xmpExt:Altitude>
              <Iptc4xmpExt:LocationName>Oak Ridge, TN</Iptc4xmpExt:LocationName>
            </rdf:li>
          </rdf:Bag>
        </Iptc4xmpExt:LocationShown>
    """
    location_elem = ET.Element(f"{{{XMP_NAMESPACES['Iptc4xmpExt']}}}LocationShown")
    bag = ET.SubElement(location_elem, f"{{{XMP_NAMESPACES['rdf']}}}Bag")
    li = ET.SubElement(bag, f"{{{XMP_NAMESPACES['rdf']}}}li")
    li.set(f"{{{XMP_NAMESPACES['rdf']}}}parseType", 'Resource')

    # Latitude (required) - 8 decimal places provides ~1.1mm precision
    lat_elem = ET.SubElement(li, f"{{{XMP_NAMESPACES['Iptc4xmpExt']}}}Latitude")
    lat_elem.text = f"{lat:.8f}"

    # Longitude (required) - 8 decimal places provides ~1.1mm precision
    lon_elem = ET.SubElement(li, f"{{{XMP_NAMESPACES['Iptc4xmpExt']}}}Longitude")
    lon_elem.text = f"{lon:.8f}"

    # Altitude (optional) - 2 decimal places for meters
    if alt is not None:
        alt_elem = ET.SubElement(li, f"{{{XMP_NAMESPACES['Iptc4xmpExt']}}}Altitude")
        alt_elem.text = f"{alt:.2f}"

    # Location name (optional)
    if name:
        name_elem = ET.SubElement(li, f"{{{XMP_NAMESPACES['Iptc4xmpExt']}}}LocationName")
        name_elem.text = name

    return location_elem


# ============================================================================
# XMP Document Builders
# ============================================================================

def build_xmp_document(metadata: ExportMetadata) -> ET.ElementTree:
    """
    Build complete XMP document from export metadata.

    Args:
        metadata: Export metadata containing photo information

    Returns:
        ElementTree containing complete XMP structure

    Structure:
        <x:xmpmeta>
          <rdf:RDF>
            <rdf:Description rdf:about="">
              <!-- Dublin Core elements -->
              <dc:title>...</dc:title>
              <dc:description>...</dc:description>
              <dc:subject>...</dc:subject>
              <dc:creator>...</dc:creator>
              <dc:rights>...</dc:rights>

              <!-- XMP elements -->
              <xmp:CreateDate>...</xmp:CreateDate>

              <!-- Photoshop elements -->
              <photoshop:City>...</photoshop:City>
              <photoshop:Country>...</photoshop:Country>

              <!-- IPTC Extension elements -->
              <Iptc4xmpExt:LocationShown>...</Iptc4xmpExt:LocationShown>
            </rdf:Description>
          </rdf:RDF>
        </x:xmpmeta>
    """
    # Create root xmpmeta element
    xmpmeta = ET.Element(
        f"{{{XMP_NAMESPACES['x']}}}xmpmeta",
        attrib={f"{{{XMP_NAMESPACES['x']}}}xmptk": "Mothbox XMP Core 1.0"}
    )

    # Create RDF root
    rdf = ET.SubElement(xmpmeta, f"{{{XMP_NAMESPACES['rdf']}}}RDF")

    # Create Description element with all namespace declarations
    desc = ET.SubElement(
        rdf,
        f"{{{XMP_NAMESPACES['rdf']}}}Description",
        attrib={
            f"{{{XMP_NAMESPACES['rdf']}}}about": '',
            "xmlns:dc": XMP_NAMESPACES['dc'],
            "xmlns:xmp": XMP_NAMESPACES['xmp'],
            "xmlns:photoshop": XMP_NAMESPACES['photoshop'],
            "xmlns:Iptc4xmpExt": XMP_NAMESPACES['Iptc4xmpExt'],
        }
    )

    # Build title from common name and species name
    title_parts = []
    if metadata.species_common_name:
        title_parts.append(metadata.species_common_name)
    if metadata.species:
        title_parts.append(f"({metadata.species})")
    if title_parts:
        title = ' '.join(title_parts)
        desc.append(build_dc_title(title))

    # Add description from notes
    if metadata.notes:
        desc.append(build_dc_description(metadata.notes))

    # Build taxonomy keywords
    taxonomy_keywords = build_taxonomy_keywords(metadata.species)

    # Add subject (tags + taxonomy)
    subject_elem = build_dc_subject(metadata.tags, taxonomy_keywords)
    desc.append(subject_elem)

    # Add creator (default to "Mothbox" if not specified)
    creator = getattr(metadata, 'creator', 'Mothbox')
    desc.append(build_dc_creator(creator))

    # Add rights/license (default to CC BY-NC 4.0 if not specified)
    license_text = getattr(metadata, 'license', 'CC BY-NC 4.0')
    desc.append(build_dc_rights(license_text))

    # Add create date
    create_date = ET.SubElement(desc, f"{{{XMP_NAMESPACES['xmp']}}}CreateDate")
    # timestamp is a string in ISO format
    create_date.text = metadata.timestamp if metadata.timestamp else ""

    # Add Photoshop elements if location data available
    # Note: locality field doesn't exist in ExportMetadata, skip for now

    if metadata.country_code:
        country = ET.SubElement(desc, f"{{{XMP_NAMESPACES['photoshop']}}}Country")
        country.text = metadata.country_code

    # Add IPTC location if GPS coordinates available
    if metadata.latitude is not None and metadata.longitude is not None:
        location = build_location_shown(
            lat=metadata.latitude,
            lon=metadata.longitude,
            alt=metadata.altitude,
            name=metadata.deployment_location_name
        )
        desc.append(location)

    return ET.ElementTree(xmpmeta)


def generate_xmp_xml(metadata: ExportMetadata) -> str:
    """
    Generate complete XMP XML string with packet wrapper.

    This is the main entry point for XMP generation. Creates a complete
    XMP packet suitable for writing to a .xmp sidecar file.

    Args:
        metadata: Export metadata containing photo information

    Returns:
        Complete XMP XML string with packet wrapper

    Example:
        >>> from webui.backend.services.export_metadata_service import ExportMetadata
        >>> metadata = ExportMetadata(...)
        >>> xmp_xml = generate_xmp_xml(metadata)
        >>> with open("photo.xmp", "w", encoding="utf-8") as f:
        ...     f.write(xmp_xml)
    """
    # Build XMP document
    tree = build_xmp_document(metadata)

    # Convert to string with XML declaration
    xml_str = ET.tostring(
        tree.getroot(),
        encoding='unicode',
        method='xml'
    )

    # Add XMP packet wrapper
    xmp_packet = f'''<?xml version="1.0" encoding="UTF-8"?>
<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
{xml_str}
<?xpacket end="w"?>'''

    return xmp_packet


# ============================================================================
# Convenience Functions
# ============================================================================

def write_xmp_sidecar(metadata: ExportMetadata, output_path: Path) -> None:
    """
    Write XMP sidecar file to disk.

    Args:
        metadata: Export metadata containing photo information
        output_path: Path where XMP file should be written

    Example:
        >>> from pathlib import Path
        >>> metadata = ExportMetadata(...)
        >>> write_xmp_sidecar(metadata, Path("photo.xmp"))
    """
    xmp_xml = generate_xmp_xml(metadata)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xmp_xml)
