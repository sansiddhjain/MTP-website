
import pandas as pd
import numpy as np 
import geopandas as gpd 
import os
from shapely.geometry import Point
import math

df_village_centroid = pd.read_csv('data/village-level-metrics.csv')
df_village_nl = pd.read_csv('data/village-nightlight.csv')

df_village_nl = df_village_nl.loc[:, 'mean':'village_code_2011']

print("loaded data")

df_spots = pd.read_csv('spots/spots-intensity.csv')
df_spots['centroidx'] = pd.Series(list([np.asarray(list(map(float, x[1:-1].split()[:2])))[0] for x in df_spots['centroid']]))
df_spots['centroidy'] = pd.Series(list([np.asarray(list(map(float, x[1:-1].split()[:2])))[1] for x in df_spots['centroid']]))

# State,District,Subdistt,Town/Village,Ward,EB,Level,Name,TRU,ELG_POP,No_HH,BF_RUD,BF_INT,BF_ADV,CHH_RUD,CHH_INT,CHH_ADV,FC_RUD,FC_INT,FC_ADV,MSL_INT,MSL_ADV,MSW_RUD,MSW_INT,MSW_ADV,EMP_AL,EMP_NAL,EMP_UN,Village,Village_HHD_Cluster_MSL,District_HHD_Cluster_MSL,Village_HHD_Cluster_MSW,District_HHD_Cluster_MSW,Village_HHD_Cluster_CHH,District_HHD_Cluster_CHH,Village_HHD_Cluster_FC,District_HHD_Cluster_FC,Village_HHD_Cluster_BF,District_HHD_Cluster_BF,Village_HHD_Cluster_EMP,District_HHD_Cluster_EMP,Unnamed: 0,ID,village_code_2011,village_code_2001,CentX,CentY,Dist
# df_village_centroid = df_village_centroid.loc[:, 'village_code_2011':'CentY']
del df_village_centroid['village_code_2001']

# Returns haversine distance in kilometers between two points
def distance_haversine(point1, point2):
	dLat = math.radians(point2.y) - math.radians(point1.y)
	dLon = math.radians(point2.x) - math.radians(point1.x)
	a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(point1.y)) * math.cos(math.radians(point2.y)) * math.sin(dLon/2) * math.sin(dLon/2)
	distance = 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
	return distance

df_village = df_village_centroid.merge(df_village_nl, on = 'village_code_2011')
# df_village.to_csv('data/village-centroid-nightlight.csv')
print("saved df_village to disk")

geometry = [Point(xy) for xy in zip(df_spots['centroidx'], df_spots['centroidy'])]
df_spots.drop(['centroidx','centroidy'], axis=1, inplace=True)
crs = {'init': 'epsg:4326'}
gdf_spots = gpd.GeoDataFrame(df_spots, crs=crs, geometry=geometry)

geometry = [Point(xy) for xy in zip(df_village['CentX'], df_village['CentY'])]
df_village.drop(['CentX', 'CentY'], axis=1, inplace=True)
crs = {'init': 'epsg:4326'}
gdf_village = gpd.GeoDataFrame(df_village, crs=crs, geometry=geometry)

print("converted everything to gpd")

df_village['distance'] = pd.Series(np.zeros(df_village.shape[0], dtype='object'))
df_village['in_circle'] = pd.Series(np.zeros(df_village.shape[0], dtype='object'))
df_spots['accessibility'] = pd.Series(np.zeros(df_spots.shape[0], dtype='object'))
d0 = 100 # Radius of the circle in kilometers around the hotspot
for i in range(df_spots.shape[0]):
	point = df_spots.loc[i, 'geometry']
	df_village['distance'] = pd.Series(list([distance_haversine(point, df_village.loc[x, 'geometry']) for x in df_village.index]))
	print('Calculated distance for all villages - ' + str(i) + '.')
	df_village['in_circle'] = pd.Series(list(map(int, df_village['distance'] < d0)))
	print('Number of villages near this hotspot - ' + str(sum(df_village['distance'] < d0)))
	if sum(df_village['distance'] < d0) != 0:
		# denominator = np.nansum(np.multiply(df_village['mean'], df_village['in_circle']))
		# Earlier I was using mean nightlight of village, but I am instead using elligible population of village - ELG_POP
		denominator = np.nansum(np.multiply(df_village['ELG_POP'], df_village['in_circle']))
		df_spots.loc[i, 'accessibility'] = df_spots.loc[i, 'avg_rad']/denominator
		print("Accessibility for hotspot %s - %s" % (i, df_spots.loc[i, 'accessibility']))
	else:
		df_spots.loc[i, 'accessibility'] = float("inf")

	df_spots.to_csv('spots/spots-accessibility-elg-pop.csv')
