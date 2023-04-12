from rasterstats import zonal_stats
import os, operator
import csv

def calculateStatistic(types,raster,catchment):
	stats = zonal_stats(catchment,raster,stats=types)
	return stats
 
def calculateRainfallDayMonth(folder,catchment,label):
	months = dict()
	months = ['JAN_1','FEB_2','MAR_3','APR_4','MAY_5','JUN_6','JUL_7','AGO_8','SEP_9','OCT_10','NOV_11','DEC_12']
	typeStat = ['mean']
	monthsPrecipitation = {}


	for month in months:
		pathRaster = os.path.join(folder,'Pcp_' + label + "_" + month + ".tif")
		zs = calculateStatistic(typeStat,pathRaster,catchment)
		monthsPrecipitation[month] = zs[0]['mean']

	maxMonth = max(monthsPrecipitation.iteritems(), key=operator.itemgetter(1))[0]

	out_path_month = os.path.join(folder,'Pcp_' + label + "_" + maxMonth + ".tif")

	return maxMonth,out_path_month
 
def saveCsv(headers,content,folder):
	row_list = []
	row_list.append(headers)

	for item in content:
		row_list.append([item[0],item[1]])
	
	with open(os.path.join(folder,"rainfall_day.csv"),"w",newline='') as file:
		writer = csv.writer(file)
		writer.writerows(row_list)
			
			
			
      
#list = calculateRainfallDayMonth("/home/skaphe/Documentos/tnc/modelos/entradas/14-Day_Rainfall/","/home/skaphe/Documentos/tnc/modelos/Workspace_BasinDelineation/tmp/1_2020_10_3/in/catchment/catchment.shp","SA_1")
#saveCsv(['month','events'],list,os.getcwd())
   
#calculateStatistic(['mean'],"/home/skaphe/Documentos/tnc/modelos/entradas/03-LandCover/YEAR_0/LULC_SA_1.tif","/home/skaphe/Documentos/tnc/modelos/Workspace_BasinDelineation/tmp/1_2020_10_3/in/catchment/catchment.shp")