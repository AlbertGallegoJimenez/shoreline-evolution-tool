import arcpy
import math
import numpy as np
import pandas as pd

class TransectProcessor(object):
    def __init__(self, df, corrFactor=2):
        # Initialize the class with a DataFrame
        self.df = df.copy()
        # Set the correction factor
        self.corrFactor = corrFactor
        # Calculate the bearing differences between consecutive transects
        self.df['diffBear'] = self.df['Bearing'].diff()
        # Calculate the mean and standard deviation of the bearing differences
        self.mean_diff_bear = self.df['diffBear'].mean()
        self.std_diff_bear = self.df['diffBear'].std()

    def classify_transects(self):
        # Classify transects with large differences using the identify_values method
        """
        self.df['correctAngle'] = self.df['diffBear'].apply(
            lambda x: (x > (self.mean_diff_bear + self.corrFactor * self.std_diff_bear)) or
                      (x < (self.mean_diff_bear - self.corrFactor * self.std_diff_bear))
        )
        """
        self.df['correctAngle'] = (self.df['diffBear'] > self.corrFactor) | (self.df['diffBear'] < -self.corrFactor)

    def interpolate_angles(self):
        # Interpolate angles for transects with large differences
        self.df['newBearing'] = self.df['Bearing']
        self.df.loc[self.df['correctAngle'], 'newBearing'] = np.nan
        self.df['newBearing'] = self.df['newBearing'].interpolate(method='linear')
        # Calculate the angle that needs to be rotated
        self.df['Angle'] = self.df['newBearing'] - self.df['Bearing']

class RotateFeatures(object):
    def __init__(self, df, fclass):
        # Initialize the class by adding an angle field with the values calculated above
        arcpy.management.AddField(fclass, 'Angle', 'DOUBLE')
        
        count = 0
        with arcpy.da.UpdateCursor(fclass, 'Angle') as cursor:
            for row in cursor:
                cursor.updateRow([df.loc[count, 'Angle']])
                count += 1

        # Rebuild each polyine with rotated vertices
        with arcpy.da.UpdateCursor(fclass, ['SHAPE@', 'Angle']) as cursor:
            for row in cursor:
                linelist = []
                for part in row[0]:
                    partlist = []
                    for pnt in part:
                        if pnt is not None:
                            partlist.append(self.rotatepoint(pnt, row[0].centroid, row[1])) # Centroid is pivot point
                    linelist.append(partlist)
                row[0] = arcpy.Polyline(arcpy.Array(linelist))
                cursor.updateRow(row)

    @staticmethod
    def rotatepoint(point, pivotpoint, angle):
        # Source: https://stackoverflow.com/questions/34372480/rotate-point-about-another-point-in-degrees-python
        angle_rad = - math.radians(angle)
        ox, oy = pivotpoint.X, pivotpoint.Y
        px, py = point.X, point.Y
        qx = ox + math.cos(angle_rad) * (px - ox) - math.sin(angle_rad) * (py - oy)
        qy = oy + math.sin(angle_rad) * (px - ox) + math.cos(angle_rad) * (py - oy)    
        return arcpy.Point(qx, qy)
    

