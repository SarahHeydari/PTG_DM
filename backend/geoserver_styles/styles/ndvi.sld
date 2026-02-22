<?xml version="1.0" encoding="UTF-8"?>
<sld:StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld" xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc" xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0.0">
  <sld:NamedLayer>
    <sld:Name>ndvi</sld:Name>
    <sld:UserStyle>
      <sld:Title>NDVI</sld:Title>
      <sld:FeatureTypeStyle>
        <sld:Rule><sld:Name>-1 to 0</sld:Name><sld:RasterSymbolizer><sld:ColorMap type="ramp">
          <sld:ColorMapEntry color="#8B0000" quantity="-1.0" label="-1.0"/>
          <sld:ColorMapEntry color="#FF0000" quantity="0.0" label="0.0"/>
        </sld:ColorMap></sld:RasterSymbolizer></sld:Rule>

        <sld:Rule><sld:Name>0 to 0.3</sld:Name><sld:RasterSymbolizer><sld:ColorMap type="ramp">
          <sld:ColorMapEntry color="#FF0000" quantity="0.0" label="0.0"/>
          <sld:ColorMapEntry color="#FFFF00" quantity="0.3" label="0.3"/>
        </sld:ColorMap></sld:RasterSymbolizer></sld:Rule>

        <sld:Rule><sld:Name>0.3 to 0.6</sld:Name><sld:RasterSymbolizer><sld:ColorMap type="ramp">
          <sld:ColorMapEntry color="#FFFF00" quantity="0.3" label="0.3"/>
          <sld:ColorMapEntry color="#00FF00" quantity="0.6" label="0.6"/>
        </sld:ColorMap></sld:RasterSymbolizer></sld:Rule>

        <sld:Rule><sld:Name>0.6 to 1</sld:Name><sld:RasterSymbolizer><sld:ColorMap type="ramp">
          <sld:ColorMapEntry color="#00FF00" quantity="0.6" label="0.6"/>
          <sld:ColorMapEntry color="#006400" quantity="1.0" label="1.0"/>
        </sld:ColorMap></sld:RasterSymbolizer></sld:Rule>
      </sld:FeatureTypeStyle>
    </sld:UserStyle>
  </sld:NamedLayer>
</sld:StyledLayerDescriptor>