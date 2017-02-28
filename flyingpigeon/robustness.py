# from flyingpigeon.visualisation import map_robustness
from flyingpigeon.utils import get_variable
from flyingpigeon.utils import sort_by_filename
from flyingpigeon.utils import get_time

import logging
logger = logging.getLogger(__name__)


def method_A(resource=[], start=None, end=None, timeslice=20,
             variable=None, title=None, cmap='seismic'):
    """returns the result

    :param resource: list of paths to netCDF files
    :param start: beginning of reference period (if None (default),
                  the first year of the consistent ensemble will be detected)
    :param end: end of comparison period (if None (default), the last year of the consistent ensemble will be detected)
    :param timeslice: period length for mean calculation of reference and comparison period
    :param variable: OBSOLETE
    :param title: str to be used as title for the signal mal
    :param cmap: define the color scheme for signal map plotting

    :return: signal.nc, low_agreement_mask.nc, high_agreement_mask.nc, text.txt,  #  graphic.png,
    """
    from os.path import split
    from tempfile import mkstemp
    from cdo import Cdo
    cdo = Cdo()
    cdo.forceOutput = True

    # preparing the resource
    try:
        file_dic = sort_by_filename(resource, historical_concatination=True)
        logger.info('file names sorted experimets: %s' % len(file_dic.keys()))
    except:
        msg = 'failed to sort the input files'
        logger.exception(msg)

    # check that all datasets contains the same variable

    try:
        var_name = set()
        for key in file_dic.keys():
            var_name = var_name.union([get_variable(file_dic[key])])
        logger.debug(var_name)
    except:
        logger.exception('failed to get the variable in common')

    if len(var_name) == 1:
        variable = [str(n) for n in var_name][0]
        logger.info('varible %s detected in all members of the ensemble' % variable)
    else:
        raise Exception('none or more than one variables are found in the ensemble members')

    # TODO: drop missfitting grids

    # timemerge for seperate datasets
    try:
        mergefiles = []
        for key in file_dic.keys():
            # if variable is None:
            #     variable = get_variable(file_dic[key])
            #     logger.info('variable detected %s ' % variable)
            try:
                if type(file_dic[key]) == list and len(file_dic[key]) > 1:
                    _, nc_merge = mkstemp(dir='.', suffix='.nc')
                    mergefiles.append(cdo.mergetime(input=file_dic[key], output=nc_merge))
                else:
                    mergefiles.extend(file_dic[key])
            except:
                logger.exception('failed to merge files for %s ' % key)
        logger.info('datasets merged %s ' % mergefiles)
    except:
        msg = 'seltime and mergetime failed'
        logger.exception(msg)

    # dataset documentation
    try:
        text_src = open('infiles.txt', 'a')
        for key in file_dic.keys():
            text_src.write(key + '\n')
        text_src.close()
    except:
        msg = 'failed to write source textfile'
        logger.exception(msg)
        _, text_src = mkstemp(dir='.', suffix='.txt')

    # configure reference and compare period
    # TODO: filter files by time

    try:
        if start is None:
            st_set = set()
            en_set = set()
            for f in mergefiles:
                times = get_time(f)
                st_set.update([times[0].year])
        if end is None:
            en_set.update([times[-1].year])
            start = max(st_set)
        if end is None:
            end = min(en_set)
        logger.info('Start and End: %s - %s ' % (start, end))
        if start >= end:
            logger.error('ensemble is inconsistent!!! start year is later than end year')
    except:
        msg = 'failed to detect start and end times of the ensemble'
        logger.exception(msg)

    # set the periodes:
    try:
        start = int(start)
        end = int(end)
        if timeslice is None:
            timeslice = int((end - start) / 3)
            if timeslice == 0:
                timeslice = 1
        else:
            timeslice = int(timeslice)
        start1 = start
        start2 = start1 + timeslice - 1
        end1 = end - timeslice + 1
        end2 = end
        logger.info('timeslice and periodes set')
    except:
        msg = 'failed to set the periodes'
        logger.exception(msg)

    try:
        files = []
        for i, mf in enumerate(mergefiles):
            files.append(cdo.selyear('{0}/{1}'.format(start1, end2), input=[mf.replace(' ', '\ ')],
                         output='file_{0}_.nc'.format(i)))  # python version
        logger.info('timeseries selected from defined start to end year')
    except:
        msg = 'seltime and mergetime failed'
        logger.exception(msg)

    try:
        # ensemble mean
        nc_ensmean = cdo.ensmean(input=files, output='nc_ensmean.nc')
        logger.info('ensemble mean calculation done')
    except:
        msg = 'ensemble mean failed'
        logger.exception(msg)

    try:
        # ensemble std
        nc_ensstd = cdo.ensstd(input=files, output='nc_ensstd.nc')
        logger.info('ensemble std and calculation done')
    except:
        msg = 'ensemble std or failed'
        logger.exception(msg)

    # get the get the signal as difference from the beginning (first years) and end period (last years), :
    try:
        selyearstart = cdo.selyear('%s/%s' % (start1, start2), input=nc_ensmean, output='selyearstart.nc')
        selyearend = cdo.selyear('%s/%s' % (end1, end2), input=nc_ensmean, output='selyearend.nc')
        meanyearst = cdo.timmean(input=selyearstart, output='meanyearst.nc')
        meanyearend = cdo.timmean(input=selyearend, output='meanyearend.nc')
        signal = cdo.sub(input=[meanyearend, meanyearst], output='signal.nc')
        logger.info('Signal calculation done')
    except:
        msg = 'calculation of signal failed'
        logger.exception(msg)
        _, signal = mkstemp(dir='.', suffix='.nc')

    # get the intermodel standard deviation (mean over whole period)
    try:
        # std_selyear = cdo.selyear('%s/%s' % (end1,end2), input=nc_ensstd, output='std_selyear.nc')
        # std = cdo.timmean(input = std_selyear, output = 'std.nc')

        std = cdo.timmean(input=nc_ensstd, output='std.nc')
        std2 = cdo.mulc('2', input=std, output='std2.nc')
        logger.info('calculation of internal model std for time period done')
    except:
        msg = 'calculation of internal model std failed'
        logger.exception(msg)
    try:
        absolut = cdo.abs(input=signal, output='absolut_signal.nc')
        high_agreement_mask = cdo.gt(input=[absolut, std2],  output='large_change_with_high_model_agreement.nc')
        low_agreement_mask = cdo.lt(input=[absolut, std], output='small_signal_or_low_agreement_of_models.nc')
        logger.info('high and low mask done')
    except:
        msg = 'calculation of robustness mask failed'
        logger.exception(msg)
        _, high_agreement_mask = mkstemp(dir='.', suffix='.nc')
        _, low_agreement_mask = mkstemp(dir='.', suffix='.nc')

    return signal, low_agreement_mask, high_agreement_mask, text_src
    #   nc_ensmean, nc_ensstd, selyearstart, selyearend
    #   # graphic,