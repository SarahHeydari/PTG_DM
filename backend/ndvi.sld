<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld"
  xmlns:sld="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">

  <sld:NamedLayer>
    <sld:Name>ndvi</sld:Name>

    <sld:UserStyle>
      <sld:Title>ndvi</sld:Title>

      <sld:FeatureTypeStyle>
        <sld:Rule>
          <sld:RasterSymbolizer>
            <sld:ColorMap type="intervals">
              <sld:ColorMapEntry color="#8B0000" quantity="-1.0" label="Very low"/>
              <sld:ColorMapEntry color="#FF0000" quantity="0.0"  label="Low"/>
              <sld:ColorMapEntry color="#FFFF00" quantity="0.3"  label="Moderate"/>
              <sld:ColorMapEntry color="#00FF00" quantity="0.6"  label="High"/>
              <sld:ColorMapEntry color="#006400" quantity="1.0"  label="Very high"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>

    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>
