<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld" xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>nbr</sld:Name>
    <sld:UserStyle>
      <sld:Title>NBR</sld:Title>
      <sld:FeatureTypeStyle>
        <sld:Rule><sld:Name>burned/high severity</sld:Name>
          <sld:RasterSymbolizer>
            <sld:ColorMap type="ramp">
              <sld:ColorMapEntry color="#8B0000" quantity="-1.0" label="-1.0"/>
              <sld:ColorMapEntry color="#FF0000" quantity="-0.1" label="-0.1"/>
              <sld:ColorMapEntry color="#FFFF00" quantity="0.1" label="0.1"/>
              <sld:ColorMapEntry color="#00FF00" quantity="0.5" label="0.5"/>
              <sld:ColorMapEntry color="#006400" quantity="1.0" label="1.0"/>
            </sld:ColorMap>
          </sld:RasterSymbolizer>
        </sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>