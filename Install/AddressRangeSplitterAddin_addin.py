import arcpy
from arcpy import mapping
import pythonaddins
import math, time

class Config(object):
    srcFieldNames = []
    srcRow = None
    geometryField = "SHAPE@"
    leftFromField = "L_F_ADD" 
    leftToField = "L_T_ADD"
    rightFromField = "R_F_ADD"
    rightToField = "R_T_ADD"
    
    @staticmethod  
    def setSrcFieldNames(fieldNames):
        Config.srcFieldNames = list(fieldNames)
        shapeIndex = Config.getFieldIndex('Shape')
        del Config.srcFieldNames[shapeIndex]
        shapeLenIndex = Config.getFieldIndex('Shape_Length')
        del Config.srcFieldNames[shapeLenIndex]
    
    @staticmethod  
    def setSrcRow(row):
        Config.srcRow  = list(row)
        shapeIndex = Config.getFieldIndex('Shape')
        del Config.srcRow[shapeIndex]
        shapeLenIndex = Config.getFieldIndex('Shape_Length')
        del Config.srcFieldNames[shapeLenIndex]
    
    @staticmethod   
    def getFieldIndex(fieldName):
        return Config.srcFieldNames.index(fieldName)
    
    @staticmethod
    def createInsertRow(lineGeometry, leftFrom, leftTo, rightFrom, rightTo):
        insertRow = list(Config.srcRow)
        insertRow[Config.getFieldIndex(Config.geometryField)] = lineGeometry 
        insertRow[Config.getFieldIndex(Config.leftFromField)] = leftFrom 
        insertRow[Config.getFieldIndex(Config.leftToField)] = leftTo
        insertRow[Config.getFieldIndex(Config.rightFromField)] = rightFrom
        insertRow[Config.getFieldIndex(Config.rightToField)] = rightTo
        
        return insertRow
    
    
class SelectedRoad(object):
    """Implementation for AddressRangeSplitterAddin_addin.selectRoadButton (Button)"""
    def __init__(self):
        self.enabled = True
        self.checked = False
        self.wholeRoad = None
        self.inFc = None
        self.layerName = None
        
    def onClick(self):
        mxd = arcpy.mapping.MapDocument("CURRENT")
        layerList = mapping.ListLayers(mxd)
        self.inFc = layerList[0]
        self.layerName = layerList[0].name
        selectedCount = int(arcpy.GetCount_management(layerList[0]).getOutput(0))
        print "Selected count: {}".format(selectedCount)
        
        if selectedCount != 1:
            return
        
        shapeFieldToRemove = "Shape"
        fieldNames = ["SHAPE@", "OID@", "*"]

        with arcpy.da.SearchCursor(self.inFc, fieldNames, explode_to_points = False) as cursor:
            for row in cursor:
                Config.srcFieldNames, Config.srcRow = self.cleanSrcRows(list(cursor.fields), list(row), [shapeFieldToRemove])
#                 Config.srcFieldNames = cursor.fields
#                 Config.srcRow = row
                self.wholeRoad = WholeRoad(row[Config.getFieldIndex("SHAPE@")], 
                              row[Config.getFieldIndex("L_F_ADD")], 
                              row[Config.getFieldIndex("L_T_ADD")], 
                              row[Config.getFieldIndex("R_F_ADD")], 
                              row[Config.getFieldIndex("R_T_ADD")])
                
                self.wholeRoad.setId(row[Config.getFieldIndex("OID@")])
                break
        
        pointSelector.enabled = True
        print "Started"
        
    def cleanSrcRows(self, srcFieldNames, srcRow, fieldsToRemove):
        for fieldName in fieldsToRemove:
            shapeIndex = srcFieldNames.index(fieldName)
            del srcFieldNames[shapeIndex]
            del srcRow[shapeIndex]
        
#         shapeLenIndex = srcFieldNames.index('Shape_Length')
#         del srcFieldNames[shapeLenIndex]
#         del srcRow[shapeLenIndex]
        return (srcFieldNames, srcRow)
#  

class SplitPointSelector(object):
    """Implementation for AddressRangeSplitterAddin_addin.pointSelector (Tool)"""
    def __init__(self):
        self.enabled = False
        self.shape = "NONE" # Can set to "Line", "Circle" or "Rectangle" for interactive shape drawing and to activate the onLine/Polygon/Circle event sinks.
        self.cursor = 3
        
    def onMouseDown(self, x, y, button, shift):
        pass
    def onMouseDownMap(self, x, y, button, shift):
        pass
    def onMouseUp(self, x, y, button, shift):
        pass
    def onMouseUpMap(self, x, y, button, shift):
        splitTime = time.time()
        startSideRoad, endSideRoad = selectRoadButton.wholeRoad.getStartAndEndSideRoads(x, y)
        print"split time: {}".format(time.time() - splitTime)
        
        insTime = time.time()    
        insCursor = arcpy.da.InsertCursor(selectRoadButton.inFc, Config.srcFieldNames)
        startSideRow = Config.createInsertRow(startSideRoad.lineGeometry, 
                                                     startSideRoad.leftFromAddr, 
                                                     startSideRoad.leftToAddr, 
                                                     startSideRoad.rightFromAddr, 
                                                     startSideRoad.rightToAddr)
        startSideId = insCursor.insertRow(startSideRow)
        
        endSideRow = Config.createInsertRow(endSideRoad.lineGeometry, 
                                                     endSideRoad.leftFromAddr, 
                                                     endSideRoad.leftToAddr, 
                                                     endSideRoad.rightFromAddr, 
                                                     endSideRoad.rightToAddr)
        endSideId = insCursor.insertRow(endSideRow)
        del insCursor
        
        self.deleteRoadById(selectRoadButton.wholeRoad.id, selectRoadButton.layerName)
        
        self.enabled = False
        
        print"ins time: {}".format(time.time() - insTime)
        
        print "Start ID: {}, End ID: {}".format(startSideId, endSideId)
        
    def onMouseMove(self, x, y, button, shift):
        pass
    def onMouseMoveMap(self, x, y, button, shift):
        pass
    def onDblClick(self):
        pass
    def onKeyDown(self, keycode, shift):
        pass
    def onKeyUp(self, keycode, shift):
        pass
    def deactivate(self):
        pass
    def onCircle(self, circle_geometry):
        pass
    def onLine(self, line_geometry):
        pass
    def onRectangle(self, rectangle_geometry):
        pass
    
    def deleteRoadById (self, id, layerName):
        layer = layerName
        #arcpy.MakeFeatureLayer_management (inFc, layer)
        arcpy.SelectLayerByAttribute_management (layer, "NEW_SELECTION", "OBJECTID = {}".format(id))
        arcpy.DeleteFeatures_management(layer)
    

class WholeRoad(object):
    
    def __init__(self, lineGeometry, L_F_Add, L_T_Add, R_F_Add, R_T_Add):
        self.lineGeometry = lineGeometry
        self.leftFromAddr = self.setAddrRangeValue(L_F_Add)
        self.leftToAddr = self.setAddrRangeValue(L_T_Add)
        self.rightFromAddr = self.setAddrRangeValue(R_F_Add)
        self.rightToAddr = self.setAddrRangeValue(R_T_Add)
        self.startSide = None
        self.endSide = None
        self.id = None
        
    def setId(self, idNum):
        self.id = idNum
        
    def setAddrRangeValue(self, addr):
        if addr is None:
            print "Bad addr value"
            return None 
        else:
            return float(addr)
        
    def getStartAndEndSideRoads(self, splitPntX, splitPntY):
        selectPnt = arcpy.Point(splitPntX, splitPntY)
        query = self.lineGeometry.queryPointAndDistance(selectPnt, use_percentage = True)
        print query
        #splitPnt = query[0]
        startSidePercent = query[1]
        endSidePercent = 1 - startSidePercent
        
        startSideSegment = self.lineGeometry.segmentAlongLine(0,  startSidePercent, use_percentage = True)
        endSideSegment = self.lineGeometry.segmentAlongLine(startSidePercent,  1, use_percentage = True)
        
        startLFrom, startLTo, startRFrom, startRTo = self.getStartAddrRangeValues(startSidePercent)
        endLFrom,  endLTo,  endRFrom,  endRTo = self.getEndAddrRangeValues(max(startLFrom, startLTo), max(startRFrom, startRTo))
        
        print "Start side new addr range: {}, {}, {}, {}".format(startLFrom, startLTo, startRFrom, startRTo)
        print "End side new addr range: {}, {}, {}, {}".format(endLFrom,  endLTo,  endRFrom,  endRTo)
        #print self.getEndAddrRangeValues(startRoadNewLeftEnd, startRoadNewRightEnd)
        
        startRoad = SplitRoad(startSideSegment, startLFrom, startLTo, startRFrom, startRTo, isStartSide = True)
        endRoad = SplitRoad(endSideSegment, endLFrom,  endLTo,  endRFrom,  endRTo, isStartSide = False)
        
        return (startRoad, endRoad)
        
    def _calculateNewRange(self, currentRange, lengthPercent):
        #currentRange = abs(fromValue - toValue)        
        newRange = round(currentRange * lengthPercent)
        
        return newRange
    
    def _caclulateNewEndValue(self, non_updatedFromOrToValue, newRange, maxOfRange):
        currentEvenOddAdjusment = non_updatedFromOrToValue %  2
        
        newEndValue = non_updatedFromOrToValue + newRange
        newEndEvenOddAdjusment = abs((newEndValue % 2) - currentEvenOddAdjusment)
        newEndValue += newEndEvenOddAdjusment
        
        if newEndValue >= maxOfRange:
            newEndValue -= 4
        
        if newEndValue < 0:
            newEndValue = 0
     
        return newEndValue
    
    def getStartAddrRangeValues(self, lenPercentage):
        newLFrom = 0
        newLTo = 0
        leftAddrRange = abs(self.leftFromAddr - self.leftToAddr)
        leftAddrRange = self._calculateNewRange(leftAddrRange, lenPercentage)
        
        newRFrom = 0
        newRTo = 0
        rightAddrRange = abs(self.rightFromAddr - self.rightToAddr)
        rightAddrRange = self._calculateNewRange(rightAddrRange, lenPercentage)
        
        if self.leftFromAddr == 0 and self.leftToAddr == 0 and self.rightFromAddr == 0 and self.rightToAddr == 0:
                    return (0, 0, 0, 0)
                
        else:
            
            if self.leftFromAddr < self.leftToAddr:
                newLTo = self._caclulateNewEndValue(self.leftFromAddr, leftAddrRange, max(self.leftFromAddr, self.leftToAddr))
                newLFrom = self.leftFromAddr    
            else:
                newLFrom = self._caclulateNewEndValue(self.leftToAddr, leftAddrRange, max(self.leftFromAddr, self.leftToAddr))
                newLTo = self.leftToAddr   
            
            if self.rightFromAddr < self.rightToAddr:
                newRTo = self._caclulateNewEndValue(self.rightFromAddr, rightAddrRange, max(self.rightFromAddr, self.rightToAddr))
                newRFrom = self.rightFromAddr 
      
            else:
                newRFrom = self._caclulateNewEndValue(self.rightToAddr, rightAddrRange, max(self.rightFromAddr, self.rightToAddr))
                newRTo = self.rightToAddr
                
        return (newLFrom, newLTo, newRFrom, newRTo)
        
    
    def getEndAddrRangeValues(self, startRoadNewLeftEnd, startRoadNewRightEnd):
        adjustValue = 2
        maxLeft = max(self.leftFromAddr, self.leftToAddr)
        maxRight = max(self.rightFromAddr, self.rightToAddr)
        if self.leftFromAddr == 0 and self.leftToAddr == 0 and self.rightFromAddr == 0 and self.rightToAddr == 0:
            adjustValue = 0                    
        
        if self.leftFromAddr < self.leftToAddr:
            newLFrom = startRoadNewLeftEnd + adjustValue
            if newLFrom >= maxLeft:
                print "Segment too short to divide address range."
            newLTo = maxLeft
            #print startRoadNewLeftEnd     
        else:
            newLTo = startRoadNewLeftEnd  + adjustValue
            if newLTo >= maxLeft:
                print "Segment too short to divide address range."
            newLFrom = maxLeft
            #print startRoadNewLeftEnd     
        
        if self.rightFromAddr < self.rightToAddr:
            newRFrom  = startRoadNewRightEnd  + adjustValue
            if newRFrom >= maxLeft:
                print "Segment too short to divide address range."                        
            newRTo = maxRight
            #print startRoadNewRightEnd      
        else:
            newRTo = startRoadNewRightEnd  + adjustValue
            if newRTo>= maxLeft:
                print "Segment too short to divide address range."                    
            newRFrom = maxRight
            #print startRoadNewRightEnd  
        
        return (newLFrom, newLTo, newRFrom, newRTo)  
            
    
    def getIndexOfSplitPoint(self):
        pass
    
    def _distanceFormula(self, x1 , y1, x2, y2):
        d = math.sqrt((math.pow((x2 - x1),2) + math.pow((y2 - y1),2)))
        return d
    
class SplitRoad(WholeRoad):
    
    def __init__(self, lineGeometry, L_F_Add, L_T_Add, R_F_Add, R_T_Add, isStartSide):
        WholeRoad.__init__(self, lineGeometry, L_F_Add, L_T_Add, R_F_Add, R_T_Add)
        self.isStartSide = isStartSide
        
    def getInsertRow(self):
        pass