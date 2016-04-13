"""
Processes for Weather Classification  
Author: Nils Hempelmann (nils.hempelmann@lsce.ipsl.fr)
Author: Cathy Nangini 
"""

from pywps.Process import WPSProcess

import logging
logger = logging.getLogger(__name__)


class WeatherRegimesProcess(WPSProcess):
    def __init__(self):
        WPSProcess.__init__(
            self,
            identifier = "weatherregimes",
            title = "Weather Regimes",
            version = "0.1",
            metadata=[
                {"title":"Weather Regimes"},
                ],
            abstract="Weather Regimes based on pressure patterns (kmean method)",
            statusSupported=True,
            storeSupported=True
            )

        # Literal Input Data
        # ------------------

        self.resources = self.addComplexInput(
            identifier="resources",
            title="NetCDF File",
            abstract="NetCDF File",
            minOccurs=1,
            maxOccurs=500,
            maxmegabites=50000,
            formats=[{"mimeType":"application/x-netcdf"}],
            )

        # self.bbox = self.addBBoxInput(
        #     identifier="bbox",
        #     title="Bounding Box",
        #     abstract="Region for weather classification",
        #     minOccurs=1,
        #     maxOccurs=1,
        #     crss=['EPSG:4326']
        #     )


        self.BBox = self.addLiteralInput(
            identifier="BBox",
            title="Region",
            abstract="coordinates to define the region: (minlon,minlat,maxlon,maxlat)",
            default='-80,50,22.5,70', #"-80,22.5,50,70",
            type=type(''),
            minOccurs=1,
            maxOccurs=1,
            )

        self.time_region = self.addLiteralInput(
            identifier="time_region",
            title="Time region",
            abstract="Select the months to define the time region (None == whole year will be analysed)",
            default="12,1,2",
            type=type(''),
            minOccurs=1,
            maxOccurs=1,
            allowedValues= ["10,11,12,1,2,3","4,5,6,7,8,9","12,1,2","3,4,5","6,7,8","9,10,11", "None"] #GROUPING
            )

        # self.method = self.addLiteralInput(
        #     identifier="method",
        #     title="Method",
        #     abstract="Choose a clustering method",
        #     default="kMEAN",
        #     type=type(''),
        #     minOccurs=1,
        #     maxOccurs=1,
        #     allowedValues=['tSNE', 'kMEAN']
        #     )

        self.observation = self.addLiteralInput(
            identifier="observation",
            title="Observation Data",
            abstract="Choose an observation dataset for comparison",
            default="NCEP",
            type=type(''),
            minOccurs=1,
            maxOccurs=1,
            allowedValues=['None', 'NCEP']
            )

        
        ######################
        ### define the outputs
        ######################

        #self.output_nc = self.addComplexOutput(
            #identifier="output_nc",
            #title="netCDF of required region",
            #abstract="3D timeseries",
            #formats=[{"mimeType":"application/netCDF"}],
            #asReference=True,
            #)

        self.output_clusters = self.addComplexOutput(
            identifier="output_clusters",
            title="Weather Classification Clusters",
            abstract="Weather Classification Clusters",
            formats=[{"mimeType":"image/png"}],
            asReference=True,
            )

        self.output_maps = self.addComplexOutput(
            identifier="output_maps",
            title="Pressure pattern",
            abstract="Corresponding pressure maps for Weather Regimes",
            formats=[{"mimeType":"image/png"}],
            asReference=True,
            )
        
        self.output_info = self.addComplexOutput(
            identifier="output_info",
            title="Weather Regime per date",
            abstract="Tar file containing tables of dates with appropriate weather regime association",
            formats=[{"mimeType":"application/x-tar"}],
            asReference=True,
            )         

    def execute(self):
        logger.info('Start process')
      
        try: 
            logger.info('read in the arguments')
            resources = self.getInputValues(identifier='resources')
          #  method = self.getInputValues(identifier='method')
            time_region = self.getInputValues(identifier='time_region')[0]
            bbox = self.getInputValues(identifier='BBox')[0]
            obs = self.getInputValues(identifier='observation')[0]

            logger.info('bbox %s' % str(bbox))
            logger.info('time_region %s' % str(time_region))
           # logger.info('method: %s' % str(method))
            

        except Exception as e: 
            logger.error('failed to read in the arguments %s ' % e)
        
        #bbox = '-80,22.5,50,70'
        logger.info('bbox is set to %s' % bbox)     

        #####################    
        ### get the required bbox from resource
        #####################
        # from flyingpigeon.ocgis_module import call 
        
        from flyingpigeon.utils import sort_by_filename, get_time, get_coordinates, get_values  #calc_grouping
        from flyingpigeon import weatherregimes as wr
        from flyingpigeon.visualisation import plot_kMEAN, concat_images, plot_pressuremap
        
        from numpy import savetxt, column_stack, ma, mean
        import tarfile

        ncs = sort_by_filename(resources, historical_concatination=True)

        try:
          png_clusters = []
          txt_info = []
          png_pressuremaps = []
          
          regime_dic = {}
          # open tar files
          tar_info = tarfile.open('info.tar', "w")
          logger.info('tar files prepared')
        except:
          msg = 'tar file preparation failed'
          logger.exception(msg)
          raise Exception(msg)

        
        ### Calculate reference for NCEP Data
        if obs == 'NCEP': 

          nc_ncep = wr.get_NCEP()

          subset_ncep = wr.subset(nc_ncep, bbox=bbox, time_region=time_region)
          pca_ncep = wr.get_pca(subset_ncep) 
          centroids_ncep, distance_ncep , regime_ncep  = wr.calc_kMEAN(pca_ncep)
          
          lats, lons = get_coordinates(subset_ncep)
          data_ncep = get_values(subset_ncep)

          times = get_time(subset_ncep)
          timestr = [t for t in times]
          tc = column_stack([timestr, regime_ncep])
          fn = 'NCEP_data.csv'
          
          savetxt(fn, tc, fmt='%s', delimiter=',', header='Date Time,WeatherRegime')
          tar_info.add(fn)
          
          png_clusters.append(plot_kMEAN(centroids_ncep, pca_ncep, 
            title='kMEAN month: %s [lonlat: %s]' % (time_region,bbox), sub_title='file: NCEP Data'))
          
          logger.info('kMEAN calculated for NCEP Data')
          
          ###############################
          # plot weather regimes for NCEP 
          ###############################

          subplots = []
          for i in range(4):
            d_mask = ma.masked_array(distance_ncep[:,i], mask=(regime_ncep==i))
            best_pattern = d_mask.argsort()[0:10]
            subplots.append(plot_pressuremap(data_ncep[best_pattern], 
              lats=lats, lons=lons, 
              title='Weather Regime %s: Month %s ' % (i, time_region), 
              sub_title='NCEP slp mean'))
            regime_dic['NCEP']['weather regime %s' % i] = mean(data_ncep[best_pattern], axis = 0)
          
          png_pressuremaps.append(concat_images(subplots, orientation='h'))
        
        ##############################################
        # Weather regime classification for Model data
        ##############################################
          
        for key in ncs.keys():
          
          try:
            nc = wr.subset(ncs[key], bbox=bbox, time_region=time_region, regrid_destination= subset_ncep)  
            logger.info('nc subset: %s ' % nc)
            pca = wr.get_pca(nc)            
            logger.info('PCa calculated')
          except:
            logger.debug('failed to calculate PCs')
            raise
          
          try:
            centroids, distance, regime  = wr.calc_kMEAN(pca)
            
            lats, lons = get_coordinates(nc)
            data = get_values(nc)

            times = get_time(nc)
            timestr = [t for t in times]
            tc = column_stack([timestr, regime])
            fn = '%s.csv' % key
            
            savetxt(fn, tc, fmt='%s', delimiter=',', header='Date Time,WeatherRegime')
            tar_info.add(fn)
            
            png_clusters.append(plot_kMEAN(centroids, pca, title='kMEAN month: %s [lonlat: %s]' % (time_region,bbox), sub_title='file: %s' % key))
            logger.info('kMEAN calculated for %s ' % key)
            
            subplots = []
            
            ################################
            # plot weather regimes for Model
            ################################

            for i in range(4):
              d_mask = ma.masked_array(distance[:,i], mask=(regime==i))
              best_pattern = d_mask.argsort()[0:10]
              subplots.append(plot_pressuremap(data[best_pattern],lats=lats, lons=lons,title='Weather Regime %s: Month %s ' % (i, time_region), sub_title='file: %s' % key))
              regime_dic[key]['weather regime %s' % i] = mean(data[best_pattern], axis = 0)

            png_pressuremaps.append(concat_images(subplots, orientation='h'))  
          except:
            logger.debug('faild to calculate cluster for %s' % key )
            raise

        ######################
        # concatinate pictures
        ######################

        c_clusters = concat_images(png_clusters, orientation='v')
        c_maps = concat_images(png_pressuremaps, orientation='v')
                      
        try:
          tar_info.close()  
          logger.info('tar files closed')
        except Exception as e:
          logger.exception('tar file closing failed')

        self.output_clusters.setValue( c_clusters  )
        self.output_maps.setValue( c_maps  )
        self.output_info.setValue('info.tar')