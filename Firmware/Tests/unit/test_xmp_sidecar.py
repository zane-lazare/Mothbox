"""
Unit tests for XMP sidecar library.

Tests XMP metadata generation for iNaturalist export compatibility.
Covers Dublin Core, XMP, IPTC Extension, and Photoshop namespaces.
"""

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from webui.backend.lib.xmp_sidecar import (
    XMP_NAMESPACES,
    build_dc_creator,
    build_dc_description,
    build_dc_rights,
    build_dc_subject,
    build_dc_title,
    build_location_shown,
    build_xmp_document,
    generate_xmp_xml,
    get_xmp_sidecar_filename,
    validate_xmp_xml,
    write_xmp_sidecar,
)
from webui.backend.services.export_metadata_service import ExportMetadata

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def minimal_metadata():
    """Minimal metadata with only required fields."""
    return ExportMetadata(
        photo_path="/photos/photo.jpg",
        filename="photo.jpg",
        timestamp="2024-01-15T10:30:00Z",
    )


@pytest.fixture
def full_metadata():
    """Complete metadata with all optional fields populated."""
    return ExportMetadata(
        photo_path="/photos/moth_2024_01_15__10_30_00.jpg",
        filename="moth_2024_01_15__10_30_00.jpg",
        timestamp="2024-01-15T10:30:00Z",
        tags=["moth", "nocturnal", "lepidoptera"],
        species="Actias luna",
        species_common_name="Luna Moth",
        notes="Beautiful green moth with long tails. Captured during night survey.",
        latitude=35.9606,
        longitude=-83.9207,
        altitude=350.5,
        deployment_location_name="Oak Ridge National Laboratory, TN",
        deployment_name="Oak Ridge Forest Survey 2024",
        mothbox_id="mothbox-001",
        firmware_version="5.2.1",
        country_code="US",
    )


# ============================================================================
# Test Constants
# ============================================================================

class TestXMPConstants:
    """Test XMP namespace definitions."""

    def test_xmp_namespaces_defined(self):
        """Test that all required XMP namespaces are defined."""
        assert 'x' in XMP_NAMESPACES
        assert 'rdf' in XMP_NAMESPACES
        assert 'dc' in XMP_NAMESPACES
        assert 'xmp' in XMP_NAMESPACES
        assert 'photoshop' in XMP_NAMESPACES
        assert 'Iptc4xmpCore' in XMP_NAMESPACES
        assert 'Iptc4xmpExt' in XMP_NAMESPACES
        assert 'exif' in XMP_NAMESPACES

    def test_namespace_uris_valid(self):
        """Test that namespace URIs are valid."""
        assert XMP_NAMESPACES['x'] == 'adobe:ns:meta/'
        assert XMP_NAMESPACES['rdf'] == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
        assert XMP_NAMESPACES['dc'] == 'http://purl.org/dc/elements/1.1/'
        assert XMP_NAMESPACES['xmp'] == 'http://ns.adobe.com/xap/1.0/'
        assert 'iptc.org' in XMP_NAMESPACES['Iptc4xmpExt'].lower()


# ============================================================================
# Test XML Utilities
# ============================================================================

class TestXMLUtilities:
    """Test XML utility functions."""

    def test_validate_xmp_xml_valid(self):
        """Test validation of valid XMP XML."""
        valid_xml = '''<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description rdf:about=""/>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''
        assert validate_xmp_xml(valid_xml) is True

    def test_validate_xmp_xml_invalid(self):
        """Test validation of invalid XML."""
        invalid_xml = '<unclosed tag'
        assert validate_xmp_xml(invalid_xml) is False

    def test_validate_xmp_xml_empty(self):
        """Test validation of empty string."""
        assert validate_xmp_xml("") is False


# ============================================================================
# Test Filename Conversion
# ============================================================================

class TestFilenameConversion:
    """Test XMP sidecar filename generation."""

    def test_jpg_to_xmp(self):
        """Test .jpg -> .xmp conversion."""
        assert get_xmp_sidecar_filename("photo.jpg") == "photo.xmp"

    def test_jpeg_to_xmp(self):
        """Test .jpeg -> .xmp conversion."""
        assert get_xmp_sidecar_filename("photo.jpeg") == "photo.xmp"

    def test_uppercase_jpg(self):
        """Test uppercase .JPG extension."""
        assert get_xmp_sidecar_filename("photo.JPG") == "photo.xmp"

    def test_complex_filename(self):
        """Test complex filename with multiple dots."""
        assert get_xmp_sidecar_filename("moth_2024_01_15__10_30_00.jpg") == "moth_2024_01_15__10_30_00.xmp"

    def test_path_object(self):
        """Test Path object input."""
        path = Path("photos/moth.jpg")
        assert get_xmp_sidecar_filename(path) == "moth.xmp"

    def test_no_extension(self):
        """Test filename without extension."""
        assert get_xmp_sidecar_filename("photo") == "photo.xmp"


# ============================================================================
# Test Dublin Core Elements
# ============================================================================

class TestDublinCoreElements:
    """Test Dublin Core metadata element generation."""

    def test_build_dc_title(self):
        """Test dc:title with rdf:Alt structure."""
        element = build_dc_title("Luna Moth (Actias luna)")
        assert element.tag.endswith('title')

        # Check rdf:Alt structure
        alt = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Alt')
        assert alt is not None

        # Check rdf:li with xml:lang
        li = alt.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert li is not None
        assert li.get('{http://www.w3.org/XML/1998/namespace}lang') == 'x-default'
        assert li.text == "Luna Moth (Actias luna)"

    def test_build_dc_title_special_chars(self):
        """Test dc:title with special characters."""
        element = build_dc_title('Moth & "Butterfly"')
        li = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        # ElementTree handles escaping automatically
        assert li.text == 'Moth & "Butterfly"'

    def test_build_dc_description(self):
        """Test dc:description with rdf:Alt structure."""
        element = build_dc_description("A beautiful moth specimen")
        assert element.tag.endswith('description')

        alt = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Alt')
        assert alt is not None

        li = alt.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert li is not None
        assert li.text == "A beautiful moth specimen"

    def test_build_dc_description_multiline(self):
        """Test dc:description with multiline text."""
        text = "Line 1\nLine 2\nLine 3"
        element = build_dc_description(text)
        li = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert li.text == text

    def test_build_dc_subject_tags_only(self):
        """Test dc:subject with only user tags."""
        element = build_dc_subject(tags=["moth", "nocturnal"], taxonomy_keywords=[])
        assert element.tag.endswith('subject')

        bag = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
        assert bag is not None

        items = bag.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert len(items) == 2
        texts = [item.text for item in items]
        assert "moth" in texts
        assert "nocturnal" in texts

    def test_build_dc_subject_taxonomy_only(self):
        """Test dc:subject with only taxonomy keywords."""
        taxonomy = ["taxonomy:kingdom=Animalia", "taxonomy:species=Actias luna"]
        element = build_dc_subject(tags=[], taxonomy_keywords=taxonomy)

        bag = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
        items = bag.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert len(items) == 2
        texts = [item.text for item in items]
        assert "taxonomy:kingdom=Animalia" in texts
        assert "taxonomy:species=Actias luna" in texts

    def test_build_dc_subject_combined(self):
        """Test dc:subject with both tags and taxonomy."""
        element = build_dc_subject(
            tags=["moth", "nocturnal"],
            taxonomy_keywords=["taxonomy:kingdom=Animalia", "taxonomy:species=Actias luna"]
        )

        bag = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
        items = bag.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert len(items) == 4
        texts = [item.text for item in items]
        assert "moth" in texts
        assert "nocturnal" in texts
        assert "taxonomy:kingdom=Animalia" in texts
        assert "taxonomy:species=Actias luna" in texts

    def test_build_dc_subject_empty(self):
        """Test dc:subject with no keywords."""
        element = build_dc_subject(tags=[], taxonomy_keywords=[])

        bag = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
        items = bag.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert len(items) == 0

    def test_build_dc_creator(self):
        """Test dc:creator with rdf:Seq structure."""
        element = build_dc_creator("Mothbox")
        assert element.tag.endswith('creator')

        seq = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Seq')
        assert seq is not None

        li = seq.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert li is not None
        assert li.text == "Mothbox"

    def test_build_dc_rights(self):
        """Test dc:rights with rdf:Alt structure."""
        element = build_dc_rights("CC BY-NC 4.0")
        assert element.tag.endswith('rights')

        alt = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Alt')
        assert alt is not None

        li = alt.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert li is not None
        assert li.get('{http://www.w3.org/XML/1998/namespace}lang') == 'x-default'
        assert li.text == "CC BY-NC 4.0"


# ============================================================================
# Test IPTC Extension Elements
# ============================================================================

class TestIPTCExtensionElements:
    """Test IPTC Extension metadata element generation."""

    def test_build_location_shown_full(self):
        """Test location with all fields."""
        element = build_location_shown(
            lat=35.9606,
            lon=-83.9207,
            alt=350.5,
            name="Oak Ridge, TN"
        )
        assert element.tag.endswith('LocationShown')

        bag = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
        assert bag is not None

        li = bag.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        assert li is not None
        assert li.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}parseType') == 'Resource'

        # Check coordinate fields (8 decimal places for lat/lon, 2 for altitude)
        lat_elem = li.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}Latitude')
        assert lat_elem is not None
        assert lat_elem.text == "35.96060000"

        lon_elem = li.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}Longitude')
        assert lon_elem is not None
        assert lon_elem.text == "-83.92070000"

        alt_elem = li.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}Altitude')
        assert alt_elem is not None
        assert alt_elem.text == "350.50"

        name_elem = li.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}LocationName')
        assert name_elem is not None
        assert name_elem.text == "Oak Ridge, TN"

    def test_build_location_shown_no_altitude(self):
        """Test location without altitude."""
        element = build_location_shown(
            lat=35.9606,
            lon=-83.9207,
            alt=None,
            name="Oak Ridge, TN"
        )

        bag = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
        li = bag.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')

        alt_elem = li.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}Altitude')
        assert alt_elem is None

    def test_build_location_shown_no_name(self):
        """Test location without name."""
        element = build_location_shown(
            lat=35.9606,
            lon=-83.9207,
            alt=350.5,
            name=None
        )

        bag = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
        li = bag.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')

        name_elem = li.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}LocationName')
        assert name_elem is None

    def test_build_location_shown_coordinates_only(self):
        """Test location with only coordinates."""
        element = build_location_shown(
            lat=35.9606,
            lon=-83.9207,
            alt=None,
            name=None
        )

        bag = element.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
        li = bag.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')

        lat_elem = li.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}Latitude')
        assert lat_elem is not None

        lon_elem = li.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}Longitude')
        assert lon_elem is not None


# ============================================================================
# Test XMP Document Generation
# ============================================================================

class TestXMPDocumentGeneration:
    """Test complete XMP document generation."""

    def test_build_xmp_document_minimal(self, minimal_metadata):
        """Test XMP document with minimal metadata."""
        tree = build_xmp_document(minimal_metadata)
        root = tree.getroot()

        # Check root element
        assert root.tag.endswith('xmpmeta')

        # Check RDF structure
        rdf = root.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF')
        assert rdf is not None

        # Check Description
        desc = rdf.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description')
        assert desc is not None
        assert desc.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about') == ''

    def test_build_xmp_document_full(self, full_metadata):
        """Test XMP document with full metadata."""
        tree = build_xmp_document(full_metadata)
        root = tree.getroot()

        # Find Description element
        desc = root.find('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description')
        assert desc is not None

        # Check dc:title
        title = desc.find('.//{http://purl.org/dc/elements/1.1/}title')
        assert title is not None

        # Check dc:description
        description = desc.find('.//{http://purl.org/dc/elements/1.1/}description')
        assert description is not None

        # Check dc:subject
        subject = desc.find('.//{http://purl.org/dc/elements/1.1/}subject')
        assert subject is not None

        # Check dc:creator
        creator = desc.find('.//{http://purl.org/dc/elements/1.1/}creator')
        assert creator is not None

        # Check dc:rights
        rights = desc.find('.//{http://purl.org/dc/elements/1.1/}rights')
        assert rights is not None

        # Check xmp:CreateDate
        create_date = desc.find('.//{http://ns.adobe.com/xap/1.0/}CreateDate')
        assert create_date is not None
        assert create_date.text == "2024-01-15T10:30:00Z"

        # Check LocationShown
        location = desc.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}LocationShown')
        assert location is not None

    def test_build_xmp_document_no_location(self, minimal_metadata):
        """Test XMP document without location data."""
        tree = build_xmp_document(minimal_metadata)
        root = tree.getroot()

        # LocationShown should not be present
        location = root.find('.//{http://iptc.org/std/Iptc4xmpExt/2008-02-29/}LocationShown')
        assert location is None

    def test_build_xmp_document_taxonomy(self, full_metadata):
        """Test XMP document includes taxonomy keywords."""
        tree = build_xmp_document(full_metadata)
        root = tree.getroot()

        # Find dc:subject bag items
        bag = root.find('.//{http://purl.org/dc/elements/1.1/}subject/{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Bag')
        assert bag is not None

        items = bag.findall('.//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li')
        texts = [item.text for item in items]

        # Check for taxonomy keywords (from Darwin Core mapping)
        taxonomy_present = any('taxonomy:' in text for text in texts)
        assert taxonomy_present

    def test_generate_xmp_xml_minimal(self, minimal_metadata):
        """Test XML string generation with minimal metadata."""
        xml = generate_xmp_xml(minimal_metadata)

        # Check XMP packet wrapper
        assert '<?xpacket begin=""' in xml
        assert '<?xpacket end="w"?>' in xml

        # Check basic structure
        assert '<x:xmpmeta' in xml
        assert '<rdf:RDF' in xml
        assert '<rdf:Description' in xml

        # Validate XML
        assert validate_xmp_xml(xml) is True

    def test_generate_xmp_xml_full(self, full_metadata):
        """Test XML string generation with full metadata."""
        xml = generate_xmp_xml(full_metadata)

        # Check presence of all expected elements
        assert 'dc:title' in xml
        assert 'dc:description' in xml
        assert 'dc:subject' in xml
        assert 'dc:creator' in xml
        assert 'dc:rights' in xml
        assert 'xmp:CreateDate' in xml
        assert 'Iptc4xmpExt:LocationShown' in xml

        # Check specific values
        assert 'Luna Moth' in xml
        assert 'Actias luna' in xml
        assert 'Beautiful green moth' in xml
        assert '35.9606' in xml
        assert '-83.9207' in xml
        assert 'Oak Ridge' in xml

        # Validate XML
        assert validate_xmp_xml(xml) is True

    def test_generate_xmp_xml_encoding(self, minimal_metadata):
        """Test XML encoding declaration."""
        xml = generate_xmp_xml(minimal_metadata)

        # Should include UTF-8 encoding
        assert 'utf-8' in xml or 'UTF-8' in xml

    def test_generate_xmp_xml_namespaces(self, minimal_metadata):
        """Test all required namespaces are declared."""
        xml = generate_xmp_xml(minimal_metadata)

        # Check namespace declarations
        assert 'xmlns:x="adobe:ns:meta/"' in xml
        assert 'xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"' in xml
        assert 'xmlns:dc="http://purl.org/dc/elements/1.1/"' in xml
        assert 'xmlns:xmp="http://ns.adobe.com/xap/1.0/"' in xml

    def test_generate_xmp_xml_well_formed(self, full_metadata):
        """Test generated XML is well-formed and parseable."""
        xml = generate_xmp_xml(full_metadata)

        # Should be parseable by ElementTree
        try:
            # Remove xpacket processing instructions for parsing
            xml_content = xml
            # Remove xpacket PIs more carefully
            import re
            xml_content = re.sub(r'<\?xpacket[^?]*\?>', '', xml_content)

            ET.fromstring(xml_content.strip())
            well_formed = True
        except ET.ParseError:
            well_formed = False

        assert well_formed is True


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_tags_list(self, minimal_metadata):
        """Test handling of empty tags list."""
        xml = generate_xmp_xml(minimal_metadata)
        assert validate_xmp_xml(xml) is True

    def test_none_species_name(self, minimal_metadata):
        """Test handling of None species name."""
        xml = generate_xmp_xml(minimal_metadata)
        # Should not contain species in title since it's None
        assert 'None' not in xml

    def test_special_characters_in_notes(self, minimal_metadata):
        """Test special characters in notes field."""
        minimal_metadata.notes = 'Test & "quotes" <tags> \'apostrophes\''
        xml = generate_xmp_xml(minimal_metadata)

        # Should be properly escaped in XML
        assert validate_xmp_xml(xml) is True

    def test_unicode_in_location(self, minimal_metadata):
        """Test Unicode characters in location name."""
        minimal_metadata.deployment_location_name = "Montréal, Québec, 日本"
        minimal_metadata.latitude = 45.5017
        minimal_metadata.longitude = -73.5673
        xml = generate_xmp_xml(minimal_metadata)

        assert "Montréal" in xml
        assert "Québec" in xml
        assert "日本" in xml
        assert validate_xmp_xml(xml) is True

    def test_very_long_description(self, minimal_metadata):
        """Test handling of very long description."""
        minimal_metadata.notes = "A" * 10000  # 10k characters
        xml = generate_xmp_xml(minimal_metadata)
        assert validate_xmp_xml(xml) is True

    def test_negative_coordinates(self, minimal_metadata):
        """Test negative latitude/longitude."""
        minimal_metadata.latitude = -33.8688
        minimal_metadata.longitude = 151.2093
        xml = generate_xmp_xml(minimal_metadata)

        assert '-33.8688' in xml
        assert '151.2093' in xml

    def test_zero_altitude(self, minimal_metadata):
        """Test altitude of exactly 0."""
        minimal_metadata.latitude = 0.0
        minimal_metadata.longitude = 0.0
        minimal_metadata.altitude = 0.0
        xml = generate_xmp_xml(minimal_metadata)

        # 0.0 should be included
        assert 'Altitude' in xml

    def test_future_timestamp(self):
        """Test handling of future timestamp."""
        future_metadata = ExportMetadata(
            photo_path="/photos/photo.jpg",
            filename="photo.jpg",
            timestamp="2099-12-31T23:59:59Z",
        )
        xml = generate_xmp_xml(future_metadata)
        assert '2099-12-31' in xml

    def test_maximum_precision_coordinates(self, minimal_metadata):
        """Test maximum precision GPS coordinates."""
        minimal_metadata.latitude = 35.960634567890123
        minimal_metadata.longitude = -83.920745678901234
        minimal_metadata.altitude = 350.123456789
        xml = generate_xmp_xml(minimal_metadata)

        # Should preserve high precision
        assert '35.96063' in xml
        assert '-83.92074' in xml

    def test_write_xmp_sidecar(self, minimal_metadata, tmp_path):
        """Test writing XMP sidecar file to disk."""
        output_path = tmp_path / "photo.xmp"
        write_xmp_sidecar(minimal_metadata, output_path)

        # File should exist
        assert output_path.exists()

        # File should contain valid XMP
        with open(output_path, encoding='utf-8') as f:
            content = f.read()

        assert validate_xmp_xml(content) is True
        assert 'xmp:CreateDate' in content
        assert '2024-01-15' in content
