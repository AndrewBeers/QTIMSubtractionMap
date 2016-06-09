""" This is Step 6, the final step. This merely takes the label volume
	and applies it to the pre- and post-contrast images. It also does
	some volume rendering. There is much left to do on this step, including
	screenshots and manual cleanup of erroneous pixels. A reset button upon
	completion would also be helpful. This step has yet to be fully commented.
"""

from __main__ import qt, ctk, slicer

from BeersSingleStep import *
from Helper import *

import string

""" ReviewStep inherits from BeersSingleStep, with itself inherits
	from a ctk workflow class. 
"""

class ReviewStep( BeersSingleStep ) :

	def __init__( self, stepid ):

		""" This method creates a drop-down menu that includes the whole step.
			The description also acts as a tooltip for the button. There may be 
			some way to override this. The initialize method is inherited
			from ctk.
		"""

		self.initialize( stepid )
		self.setName( '6. Review' )
		self.setDescription( 'The segment from the subtraction map is now overlaid on your post-contrast image. Use the threshold bar below to edit the volume rendering node. Use the official Volume Rendering module for more specific visualization.' )

		self.__vrDisplayNode = None
		self.__threshold = [ -1, -1 ]
		
		# initialize VR stuff
		self.__vrLogic = slicer.modules.volumerendering.logic()
		self.__vrOpacityMap = None

		self.__roiSegmentationNode = None
		self.__roiVolume = None

		self.__parent = super( ReviewStep, self )

	def createUserInterface( self ):

		""" This step is mostly empty. A volume rendering threshold is added to be useful.
		"""

		self.__layout = self.__parent.createUserInterface()

		threshLabel = qt.QLabel('Choose Volume Rendering Threshold:')
		self.__threshRange = slicer.qMRMLRangeWidget()
		self.__threshRange.decimals = 0
		self.__threshRange.singleStep = 1

		self.__layout.addRow(threshLabel, self.__threshRange)
		self.__threshRange.connect('valuesChanged(double,double)', self.onThresholdChanged)
		qt.QTimer.singleShot(0, self.killButton)

	def onThresholdChanged(self): 
	
		if self.__vrOpacityMap == None:
			return
		
		range0 = self.__threshRange.minimumValue
		range1 = self.__threshRange.maximumValue

		self.__vrOpacityMap.RemoveAllPoints()
		self.__vrOpacityMap.AddPoint(range0-75,0)
		self.__vrOpacityMap.AddPoint(range0,1)
		self.__vrOpacityMap.AddPoint(range1,1)
		self.__vrOpacityMap.AddPoint(range1+75,0)

	def killButton(self):

		# ctk creates a useless final page button. This method gets rid of it.
		bl = slicer.util.findChildren(text='ReviewStep')
		if len(bl):
			bl[0].hide()

	def validate( self, desiredBranchId ):

		# For now, no validation required.
		self.__parent.validationSucceeded(desiredBranchId)

	def onEntry(self, comingFrom, transitionType):
		super(ReviewStep, self).onEntry(comingFrom, transitionType)


		pNode = self.parameterNode()

		baselineVolumeID = pNode.GetParameter('baselineVolumeID')
		self.__followupVolumeID = pNode.GetParameter('followupVolumeID')
		self.__followupVolumeNode = Helper.getNodeByID(self.__followupVolumeID)
		vrDisplayNodeID = pNode.GetParameter('vrDisplayNodeID')
		self.__roiSegmentationNode = Helper.getNodeByID(pNode.GetParameter('croppedSubtractVolumeSegmentationID'))
		self.__roiVolumeNode = Helper.getNodeByID(pNode.GetParameter('croppedSubtractVolumeID'))

		followupRange = self.__followupVolumeNode.GetImageData().GetScalarRange()
		ROIRange = self.__roiSegmentationNode.GetImageData().GetScalarRange()
		self.__threshRange.minimum = followupRange[0]
		self.__threshRange.maximum = followupRange[1]

		if self.__vrDisplayNode == None:
			if vrDisplayNodeID != '':
				self.__vrDisplayNode = slicer.mrmlScene.GetNodeByID(vrDisplayNodeID)

		self.__vrDisplayNode.SetCroppingEnabled(0)
		self.__followupVolumeNode.AddAndObserveDisplayNodeID(self.__vrDisplayNode.GetID())
		Helper.InitVRDisplayNode(self.__vrDisplayNode, self.__followupVolumeID, '')

		self.__vrOpacityMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetScalarOpacity()
		vrColorMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetRGBTransferFunction()

		vrColorMap.RemoveAllPoints()
		vrColorMap.AddRGBPoint(0, 0, 0, 0) 
		vrColorMap.AddRGBPoint(followupRange[0]-1, 0, 0, 0) 
		vrColorMap.AddRGBPoint(followupRange[0], 0.8, 0.8, 0) 
		vrColorMap.AddRGBPoint(followupRange[1], 0.8, 0.8, 0) 
		vrColorMap.AddRGBPoint(followupRange[1]+1, 0, 0, 0) 

		self.__vrDisplayNode.VisibilityOn()

		threshRange = [self.__threshRange.minimumValue, self.__threshRange.maximumValue]
		self.__vrOpacityMap.RemoveAllPoints()
		self.__vrOpacityMap.AddPoint(threshRange[1]/2-75,0)
		self.__vrOpacityMap.AddPoint(threshRange[1]/2,1)
		self.__vrOpacityMap.AddPoint(threshRange[1]/2+200,1)
		self.__vrOpacityMap.AddPoint(threshRange[1]/2+250,0)

		Helper.SetBgFgVolumes(baselineVolumeID,self.__followupVolumeID)
		Helper.SetLabelVolume(self.__roiSegmentationNode.GetID())

		self.onThresholdChanged()

		pNode.SetParameter('currentStep', self.stepid)
	
		qt.QTimer.singleShot(0, self.killButton)

	def onExit(self, goingTo, transitionType):   
		# extra error checking, in case the user manages to click ReportROI button
		super(BeersSingleStep, self).onExit(goingTo, transitionType) 