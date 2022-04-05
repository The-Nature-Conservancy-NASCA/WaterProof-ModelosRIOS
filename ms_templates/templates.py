
mapserver_template_file = """
MAP
  NAME          "Waterproof_result_data"
  CONFIG        "MS_ERRORFILE" "stderr"
  EXTENT        -8412553 503524 -8391124 524032
  UNITS         meters
  STATUS        ON
  SIZE          500 500
  RESOLUTION 91
  DEFRESOLUTION 91
  PROJECTION
    "init=epsg:3857"
  END

  INCLUDE '../../metadata_mapserver.map'

  LAYER
    NAME "Catchment"
    STATUS ON
    TYPE POLYGON
    METADATA
      'wfs_title'                    'Catchment'
      'wfs_abstract'                 'Layer containing the example data'
      'wfs_srs'                      'EPSG:4326 EPSG:3857 EPSG:4258 EPSG:900913 CRS:84'      
      'wfs_extent'                   '-8412553 503524 -8391124 524032'
      'wfs_bbox_extended'            'true'
      'wfs_enable_request'           '*'
      'wfs_include_items'            'all'
      'wfs_getfeature_formatlist'    'OGRGML3,OGRGML32,GEOJSON,JSON'
      'gml_include_items'            'all'
      'gml_exclude_items'            'id'
      'gml_featureid'                'id'
      'gml_geometries'               'geom'
      'gml_types'                    'auto'
      'wms_title'                    'catchment'
      'wms_extent'                   '-8412553 503524 -8391124 524032'    
      'wms_abstract'                 'Layer containing the catchment data'
      'wms_srs'                      'EPSG:4326 EPSG:3857 EPSG:4258 EPSG:900913 CRS:84'
      'wms_keywordlist'              'catchment,unknown'
      'wms_include_items'            'all'
    END
    CLASSGROUP 'catchment:style'
    CLASS
      NAME 'Catchment'
      GROUP 'catchment:style'
      STYLE
        OUTLINECOLOR 0 0  125
        WIDTH 2
      END
    END
    INCLUDE '../../waterproof.projection'
    DATA 'in/catchment/catchment.shp'    
    TEMPLATE /srv/data/example.html
  END # LAYER

  # WI Layers
  LAYER
    NAME 'LULC_YEAR_0'
    METADATA
      'ows_title' 'WI_%intake%_LULC_%region%_YEAR_0'
    END   
    INCLUDE '../../waterproof.projection'
    TYPE RASTER
    STATUS  OFF
    DATA 'in/04-RIOS/LULC_%region%.tif'
    INCLUDE '../../lulc_default.classes'
  END
  LAYER
    NAME 'LULC_FUTURE'
    METADATA
      'ows_title' 'WI_%intake%_LULC_SA_1_FUTURE'
    END
    INCLUDE '../../waterproof.projection'
    TYPE RASTER
    STATUS  OFF
    DATA 'in/02-PREPROC_RIOS/LULC_%region%_FUTURE.tif'
    INCLUDE '../../lulc_default.classes'
  END

  LAYER
    NAME 'LULC_LAST_YEAR'
    METADATA
      'ows_title' 'WI_%intake%_LULC_LAST_YEAR'
    END
    INCLUDE '../../waterproof.projection'
    TYPE RASTER
    STATUS  OFF
    DATA 'out/04-RIOS/1_investment_portfolio_adviser_workspace/activity_portfolios/continuous_activity_portfolios/translated_cob/activity_portfolio_continuous_year_%year%_FUTURE.tif'
    PROCESSING 'RESAMPLE=NEAREST'
    PROCESSING 'NODATA=ON'
    INCLUDE '../../lulc_default.classes'
  END

  # Models Result
  # AWY
  LAYER
    NAME 'Annual_Water_Yield'
    METADATA
      'ows_title' 'Annual Water Yield'
    END
    INCLUDE '../../waterproof.projection'
    TYPE RASTER
    STATUS  OFF
    DATA 'out/03-INVEST/AWY/YEAR_%year%/output/per_pixel/wyield_%region%.tif'
    PROCESSING 'SCALE=AUTO'
    PROCESSING 'RESAMPLE=NEAREST'
    PROCESSING 'NODATA=ON' 
    PROCESSING 'COLOR_MATCH_THRESHOLD=3'
    CLASS # Red Range
      STYLE
        RANGEITEM 'pixel'
        DATARANGE {} {}
        COLORRANGE 255 245 240 103 0 13
      END
    END
  END

  # SWY
  LAYER
    NAME 'Seasonal_Water_Yield'
    METADATA
      'ows_title' 'Seasonal Water Yield %region%'
    END
    INCLUDE '../../waterproof.projection'
    DATA 'out/03-INVEST/SWY/YEAR_%year%/B_%region%.tif'
    TYPE RASTER
    STATUS  OFF    
    PROCESSING 'SCALE=AUTO'
    PROCESSING 'RESAMPLE=NEAREST'
    PROCESSING 'NODATA=ON'
    #INCLUDE 'B_SA_1.map'
    CLASS # Green Range
      STYLE
        RANGEITEM 'pixel'
        DATARANGE {} {}
        COLORRANGE 247 252 245 0 68 27
      END
    END
  END

  # SDR
  LAYER
    NAME 'Sediment_Delivery_Ratio'
    METADATA
      'ows_title' 'Sediment Delivery Ratio'
    END
    INCLUDE '../../waterproof.projection'
    DATA 'out/03-INVEST/SDR/YEAR_%year%/sed_export_%region%.tif'
    TYPE RASTER
    STATUS  OFF
    PROCESSING 'NODATA=ON'
    CLASS # Blue Range
      STYLE
        RANGEITEM 'pixel'
        DATARANGE {} {}
        COLORRANGE 247 251 255 8 48 107
      END
    END
  END

  # NDR - Nitrogen
  LAYER
    NAME 'NDR_Nitrogen'
    METADATA
      'ows_title' 'Nutrient Delivery Ratio - Nitrogen'
    END
    INCLUDE '../../waterproof.projection'
    DATA 'out/03-INVEST/NDR/YEAR_%year%/n_export_%region%.tif'
    TYPE RASTER
    STATUS  OFF    
    PROCESSING 'SCALE=AUTO'
    PROCESSING 'RESAMPLE=NEAREST'
    PROCESSING 'NODATA=ON'
    CLASS # Purple Range
      STYLE
        RANGEITEM 'pixel'
        DATARANGE {} {}
        COLORRANGE 241 238 246 152 0 63
      END
    END
  END

  # NDR - Phosphorus
  LAYER
    NAME 'NDR_Phosphorus'
    METADATA
      'ows_title' 'Nutrient Delivery Ratio - Phosphorus'
    END
    INCLUDE '../../waterproof.projection'
    DATA 'out/03-INVEST/NDR/YEAR_%year%/p_export_%region%.tif'
    TYPE RASTER
    STATUS  OFF    
    PROCESSING 'SCALE=AUTO'
    PROCESSING 'RESAMPLE=NEAREST'
    PROCESSING 'NODATA=ON'
    CLASS # Orange Range
      STYLE
        RANGEITEM 'pixel'
        DATARANGE {} {}
        COLORRANGE 255 255 212 153 52 4
      END
    END
  END

  # Carbon Storage and Sequestration
  LAYER
    NAME 'Carbon_storage_and_sequestration'
    METADATA
      'ows_title' 'Carbon Storage and Sequestration'
    END
    INCLUDE '../../waterproof.projection'
    DATA 'out/03-INVEST/CARBON/YEAR_%year%/tot_c_cur_%region%.tif'
    TYPE RASTER
    STATUS  OFF    
    PROCESSING 'SCALE=AUTO'    
    PROCESSING 'NODATA=ON' 
    CLASS # Blue 2 Green Range
      STYLE
        RANGEITEM 'pixel'
        DATARANGE {} {}
        COLORRANGE 246 239 247 1 108 89
      END
    END   
  END  
END # MAP  
"""