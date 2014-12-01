from malleefowl import wpslogging as logging
from malleefowl.process import WPSProcess
from datetime import datetime, date
import types

# initialise
logger = logging.getLogger(__name__)

class analogs(WPSProcess):
  
  def __init__(self):
    # definition of this process
    WPSProcess.__init__(self, 
      identifier = "analogs",
      title="Days with analog pressure pattern",
      version = "0.1",
      metadata= [
              {"title": "Institut Pierre Simon Laplace", "href": "https://www.ipsl.fr/en/"}
              ],
      abstract="Search for days with analog pressure pattern",
      #extra_metadata={
          #'esgfilter': 'variable:tas,variable:evspsbl,variable:hurs,variable:pr',  #institute:MPI-M, ,time_frequency:day
          #'esgquery': 'variable:tas AND variable:evspsbl AND variable:hurs AND variable:pr' # institute:MPI-M AND time_frequency:day 
          #},
      )

    self.netcdf_file = self.addComplexInput(
      identifier="netcdf_file",
      title="NetCDF",
      abstract="URL to netCDF file",
      minOccurs=0,
      maxOccurs=1000,
      maxmegabites=5000,
      formats=[{"mimeType":"application/x-netcdf"}],
      )

    self.experiment = self.addLiteralInput(
      identifier="experiment",
      title="Data experiment",
      abstract="Choose the experiment",
      default="NCEP",
      type=type(''),
      minOccurs=1,
      maxOccurs=1,
      allowedValues=['NCEP', 'Dummy', 'Dummy']
      )
       
    self.region = self.addLiteralInput(
      identifier="region",
      title="Select Region",
      abstract="Select a predifined region",
      default="NA",
      type=type(''),
      minOccurs=1,
      maxOccurs=1,
      allowedValues=['NA', 'Dummy', 'Dummy']
      )       

    #self.bbox = self.addLiteralOutput(
      #identifier="bbox",
      #title="Bounding Box",
      #abstract="This is a BBox: (minx,miny,maxx,maxy)",
      #default="0,-90,180,90",
      #type=type(''),
      #)
         
    self.dateSt = self.addLiteralInput(
      identifier="dateSt",
      title="Start date of analyse period",
      abstract="This is a Date: 2013-07-15",
      default="2014-07-15",
      type=type(date(2014,7,15)),
      minOccurs=1,
      maxOccurs=1,
      )
    
    self.dateEn = self.addLiteralInput(
      identifier="dateEn",
      title="End date of analyse period",
      abstract="This is a Date: 2013-12-31",
      default="2013-12-31",
      type=type(date(2013,12,31)),
      minOccurs=1,
      maxOccurs=1,
      )

    self.refSt = self.addLiteralInput(
      identifier="refSt",
      title="Start reference period",
      abstract="Start YEAR of reference period",
      default="1955-01-01",
      type=type(date(1948,01,01)),
      minOccurs=1,
      maxOccurs=1,
      )
    
    self.refEn = self.addLiteralInput(
      identifier="refEn",
      title="End reference period",
      abstract="End YEAR of reference period",
      default="1957-12-31",
      type=type(date(1958,12,31)),
      minOccurs=1,
      maxOccurs=1,
      )
    
    self.ncout = self.addComplexOutput(
      identifier="ncout",
      title="netCDF inputfile",
      abstract="netCDF file of the ps valuels",
      formats=[{"mimeType":"application/netcdf"}],
      asReference=True,
      )

    self.tarout = self.addComplexOutput(
      identifier="tarout",
      title="Result tar file",
      abstract="Tar archive containing files with the analog dates",
      formats=[{"mimeType":"application/x-tar"}],
      asReference=True,
      )

    self.Rlogout = self.addComplexOutput(
      identifier="Rlogout",
      title="R-logfile",
      abstract="Logfile for the R process",
      formats=[{"mimeType":"text/plain"}],
      asReference=True,
      )

  def execute(self):

    import tempfile
    import tarfile
    import ocgis 
    from ocgis import RequestDataset
    import datetime as dt
    #from subprocess import call
    import os
    
    self.show_status('execution started at : %s '  % dt.datetime.now() , 5)

    refSt = self.getInputValues(identifier='refSt')
    refEn = self.getInputValues(identifier='refEn')
    dateSt = self.getInputValues(identifier='dateSt')
    dateEn = self.getInputValues(identifier='dateEn')
    
    refSt = dt.datetime.strptime(refSt[0],'%Y-%m-%d')
    refEn = dt.datetime.strptime(refEn[0],'%Y-%m-%d')
    dateSt = dt.datetime.strptime(dateSt[0],'%Y-%m-%d')
    dateEn = dt.datetime.strptime(dateEn[0],'%Y-%m-%d')
    
    # self.show_status( dateEn  , 15)
    
    start = min(refSt, refEn, dateSt, dateEn )
    end = max(refSt, refEn, dateSt, dateEn )
    uris = []
    (fp_tar, tarout_file) = tempfile.mkstemp(dir=".", suffix='.tar')
    tar = tarfile.open(tarout_file, "w")

    from malleefowl.download import download
    for y in range(start.year , end.year +1 , 1): 
      url = 'http://www.esrl.noaa.gov/psd/thredds/fileServer/Datasets/ncep.reanalysis.dailyavgs/surface/slp.%i.nc' % (y)
      (fp_tf, tf ) = tempfile.mkstemp(dir=".", suffix=".nc")
      (fp_tf2, tf2 ) = tempfile.mkstemp(dir=".", suffix=".nc")
      #cmd =  str('ncks -O -d lon,280.0,50.0 -d lat,22.5,70.0 %s %s' %( download(url), tf))
      cmd = ['ncks', '-O', '-d', 'lon,280.0,50.0', '-d', 'lat,22.5,70.0', download(url), tf]
      #os.system(cmd) # ["ls", "-l"])nc = wget.download(url)
      self.cmd(cmd, stdout=True)
      #cdo_cmd = 'cdo sellonlatbox,-80,50,22.5,70 %s %s ' % (tf, tf2)
      cdo_cmd = ['cdo', 'sellonlatbox,-80,50,22.5,70', tf, tf2]
      self.cmd(cdo_cmd, stdout=True)
      #os.system(cdo_cmd)
      uris.append(tf2)
      self.show_status('NCEP file year: %i  downloaded'  % (y) , 7)
      
    us = ocgis.util.helpers.get_sorted_uris_by_time_dimension(uris, variable=None)  # for time sorting
    fname = str('slp_NOA_NCEP_%i_%i' % (start.year , end.year))
    self.show_status('download done for : %s '  % (fname) , 10)

    # ocgis specifications:
    # try: 
    # if (self.getInputValues(identifier='region') == 'NOA'):
    #geom = [-80, 22.5, 50, 70.0 ] # [min x, min y, max x, max y].
    
    ocgis.env.DIR_OUTPUT = self.working_dir
    rds = RequestDataset(us, 'slp')
    ops = ocgis.OcgOperations(dataset=rds, prefix=fname,  output_format='nc', allow_empty=True, add_auxiliary_files=False)
    ret = ops.execute()
    fpath = '%s' % (ret)
    # tar.add(fpath , arcname = fpath.replace(self.working_dir, ""))
    self.show_status('ocgis subset succeded for file : %s '  % (ret) , 15)
    
    ### run R file 
    pf = str(os.path.dirname(os.path.abspath(__file__)))
    
    Rskript = os.path.join(pf + '/Rsrc/analogs.R')
    Rsource = os.path.join(pf + '/Rsrc/')
    logger.debug('found R skript : %s', Rskript)
    curdir = os.path.abspath(os.path.curdir)
    logger.debug('curdir : %s '  % (curdir))
    logger.debug('analogs.R : %s '  % (Rskript))
    os.mkdir(os.path.curdir+'/RoutDir/')
    RoutDir = os.path.join(os.path.curdir+'/RoutDir/')
    (fp_Rlog, Rlog) = tempfile.mkstemp(dir="./RoutDir/", suffix='.log')
    Rcmd = 'R --vanilla --args %s %s %s %i %i %s %s <  %s > %s ' % (ret, dateSt.date(), dateEn.date(), refSt.year, refEn.year, Rsource, curdir, Rskript, Rlog )
    #Rcmd = ['R', '--vanilla', '--args', ret, str(dateSt.date()), str(dateEn.date()), str(refSt.year), str(refEn.year), Rsource, curdir,'<', Rskript,'>', Rlog]
    logger.debug('system call : %s '  % (Rcmd))
    
    # Call the R skript
    os.system(str(Rcmd))
    #self.cmd(Rcmd, stdout=False)
    tar.add(RoutDir) # , arcname = fpath.replace(self.working_dir, ""))
    ##except Exception as e: 
      ##self.show_status('failed for file : %s '  % ( e ) , 15)
    tar.close()
    
    self.ncout.setValue(ret)
    self.Rlogout.setValue( Rlog )
    self.tarout.setValue(tarout_file)
    self.show_status('execution ended at : %s'  %  dt.datetime.now() , 100)