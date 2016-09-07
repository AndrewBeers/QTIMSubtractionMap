""" This is Step 6, the final step. This merely takes the label volume
	and applies it to the pre- and post-contrast images. It also does
	some volume rendering. There is much left to do on this step, including
	screenshots and manual cleanup of erroneous pixels. A reset button upon
	completion would also be helpful. This step has yet to be fully commented.
"""

from __main__ import qt, ctk, slicer

from BeersSingleStep import *
from Helper import *
from Editor import EditorWidget
from EditorLib import EditorLib

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

		self.__pNode = None
		self.__vrDisplayNode = None
		self.__threshold = [ -1, -1 ]
		
		# initialize VR stuff
		self.__vrLogic = slicer.modules.volumerendering.logic()
		self.__vrOpacityMap = None

		self.__roiSegmentationNode = None
		self.__roiVolume = None

		self.__parent = super( ReviewStep, self )
		self.__RestartActivated = False

	def createUserInterface( self ):

		""" This step is mostly empty. A volume rendering threshold is added to be useful.
		"""

		self.__layout = self.__parent.createUserInterface()

		self.__threshRange = slicer.qMRMLRangeWidget()
		self.__threshRange.decimals = 0
		self.__threshRange.singleStep = 1
		self.__threshRange.connect('valuesChanged(double,double)', self.onThresholdChanged)
		qt.QTimer.singleShot(0, self.killButton)

		ThreshGroupBox = qt.QGroupBox()
		ThreshGroupBox.setTitle('3D Visualization Intensity Threshold')
		ThreshGroupBoxLayout = qt.QFormLayout(ThreshGroupBox)
		ThreshGroupBoxLayout.addRow(self.__threshRange)
		self.__layout.addRow(ThreshGroupBox)

		editorWidgetParent = slicer.qMRMLWidget()
		editorWidgetParent.setLayout(qt.QVBoxLayout())
		editorWidgetParent.setMRMLScene(slicer.mrmlScene)
		self.__editorWidget = EditorWidget(parent=editorWidgetParent)
		self.__editorWidget.setup()
		self.__layout.addRow(editorWidgetParent)
		self.hideUnwantedEditorUIElements()

		RestartGroupBox = qt.QGroupBox()
		RestartGroupBox.setTitle('Restart')
		RestartGroupBoxLayout = qt.QFormLayout(RestartGroupBox)

		self.__RestartButton = qt.QPushButton('Return to Step 1')
		RestartGroupBoxLayout.addRow(self.__RestartButton)

		self.__RemoveCroppedSubtractionMap = qt.QCheckBox()
		self.__RemoveCroppedSubtractionMap.checked = True
		self.__RemoveCroppedSubtractionMap.setToolTip("Delete the cropped version of your subtaction map.")
		RestartGroupBoxLayout.addRow("Delete cropped subtraction map: ", self.__RemoveCroppedSubtractionMap)    

		self.__RemoveFullSubtracitonMap = qt.QCheckBox()
		self.__RemoveFullSubtracitonMap.checked = True
		self.__RemoveFullSubtracitonMap.setToolTip("Delete the full version of your subtaction map.")
		RestartGroupBoxLayout.addRow("Delete full subtraction map: ", self.__RemoveFullSubtracitonMap)    

		self.__RemoveROI = qt.QCheckBox()
		self.__RemoveROI.checked = False
		self.__RemoveROI.setToolTip("Delete the ROI resulting from your subtaction map.")
		RestartGroupBoxLayout.addRow("Delete ROI: ", self.__RemoveROI)    
		
		# self.__RestartButton.setEnabled(0)

		self.__RestartButton.connect('clicked()', self.Restart)
		self.__RestartActivated = True

		self.__layout.addRow(RestartGroupBox)

	def hideUnwantedEditorUIElements(self):
		print self.__editorWidget.editBoxFrame
		self.__editorWidget.volumes.hide()
		print dir(self.__editorWidget)
		print slicer.util.findChildren()
		# for widgetName in slicer.util.findChildren(self.__editorWidget.editBoxFrame):
		for widgetName in slicer.util.findChildren(self.__editorWidget.helper):
			# widget = slicer.util.findChildren(self.__editorWidget.editBoxFrame)
			print widgetName.objectName
			# print widgetName.parent.name
			# widgetName.hide()
		for widget in ['DrawEffectToolButton', 'RectangleEffectToolButton', 'IdentifyIslandsEffectToolButton', 'RemoveIslandsEffectToolButton', 'SaveIslandEffectToolButton', 'RowFrame2']:
			slicer.util.findChildren(self.__editorWidget.editBoxFrame, widget)[0].hide()
		print slicer.util.findChildren('','EditColorFrame')



	def Restart( self ):
		print self.__pNode

		slicer.mrmlScene.RemoveNode(testVolume)
		
		self.__pNode.SetParameter('baselineVolumeID', None)
		self.__pNode.SetParameter('croppedSubtractVolumeID', None)
		self.__pNode.SetParameter('croppedSubtractVolumeSegmentationID', None)
		self.__pNode.SetParameter('followupVolumeID', None)
		self.__pNode.SetParameter('roiNodeID', None)
		self.__pNode.SetParameter('roiTransformID', None)
		self.__pNode.SetParameter('subtractVolumeID', None)
		self.__pNode.SetParameter('vrDisplayNodeID', None)
		self.__pNode.SetParameter('thresholdRange', None)
		if self.__RestartActivated:
			self.workflow().goForward()

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
		ex = slicer.util.findChildren('','EditColorFrame')
		if len(bl):
			bl[0].hide()
		if len(ex):
			ex[0].hide()
			print 'success'
		else:
			print 'fail'

		self.__editLabelMapsFrame = slicer.util.findChildren('','EditLabelMapsFrame')[0]
		self.__toolsColor = EditorLib.EditColor(self.__editLabelMapsFrame)

	def validate( self, desiredBranchId ):

		# For now, no validation required.
		self.__parent.validationSucceeded(desiredBranchId)

	def onEntry(self, comingFrom, transitionType):
		super(ReviewStep, self).onEntry(comingFrom, transitionType)

		# self.__RestartButton.setEnabled(1)
		self.__RestartActivated = True

		pNode = self.parameterNode()
		self.__pNode = pNode

		self.__clippingModelNode = Helper.getNodeByID(pNode.GetParameter('clippingModelNodeID'))
		print self.__clippingModelNode
		print pNode.GetParameter('clippingModelNodeID')
		self.__baselineVolumeID = pNode.GetParameter('baselineVolumeID')
		self.__followupVolumeID = pNode.GetParameter('followupVolumeID')
		self.__subtractVolumeID = pNode.GetParameter('subtractVolumeID')
		self.__roiNodeID = pNode.GetParameter('roiNodeID')
		self.__followupVolumeNode = Helper.getNodeByID(self.__followupVolumeID)
		self.__subtractVolumeNode = Helper.getNodeByID(self.__subtractVolumeID)
		self.__vrDisplayNodeID = pNode.GetParameter('vrDisplayNodeID') 
		self.__roiSegmentationNode = Helper.getNodeByID(pNode.GetParameter('croppedSubtractVolumeSegmentationID'))
		self.__roiVolumeNode = Helper.getNodeByID(pNode.GetParameter('croppedSubtractVolumeID'))

		self.__editorWidget.setMergeNode(self.__roiSegmentationNode)
		self.__clippingModelNode.GetDisplayNode().VisibilityOn()

		followupRange = self.__followupVolumeNode.GetImageData().GetScalarRange()
		ROIRange = self.__roiSegmentationNode.GetImageData().GetScalarRange()

		if self.__vrDisplayNode == None:
			if self.__vrDisplayNodeID != '':
				self.__vrDisplayNode = slicer.mrmlScene.GetNodeByID(self.__vrDisplayNodeID)

		self.__vrDisplayNode.SetCroppingEnabled(1)
		self.__followupVolumeNode.AddAndObserveDisplayNodeID(self.__vrDisplayNode.GetID())
		Helper.InitVRDisplayNode(self.__vrDisplayNode, self.__followupVolumeID, self.__roiNodeID)

		self.__threshRange.minimum = followupRange[0]
		self.__threshRange.maximum = followupRange[1]
		self.__threshRange.setValues(followupRange[1]/3, 2*followupRange[1]/3)

		self.__vrOpacityMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetScalarOpacity()
		vrColorMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetRGBTransferFunction()

		vrColorMap.RemoveAllPoints()
		vrColorMap.AddRGBPoint(followupRange[0], 0.8, 0.8, 0) 
		vrColorMap.AddRGBPoint(followupRange[1], 0.8, 0.8, 0) 


		self.__vrDisplayNode.VisibilityOn()

		# threshRange = [self.__threshRange.minimumValue, self.__threshRange.maximumValue]
		# self.__vrOpacityMap.RemoveAllPoints()
		# self.__vrOpacityMap.AddPoint(threshRange[1]/2-75,0)
		# self.__vrOpacityMap.AddPoint(threshRange[1]/2,1)
		# self.__vrOpacityMap.AddPoint(threshRange[1]/2+200,1)
		# self.__vrOpacityMap.AddPoint(threshRange[1]/2+250,0)

		Helper.SetBgFgVolumes(self.__baselineVolumeID,self.__followupVolumeID)
		Helper.SetLabelVolume(self.__roiSegmentationNode.GetID())

		self.onThresholdChanged()

		pNode.SetParameter('currentStep', self.stepid)
	
		qt.QTimer.singleShot(0, self.killButton)

	def onExit(self, goingTo, transitionType):   
		# extra error checking, in case the user manages to click ReportROI button
		super(BeersSingleStep, self).onExit(goingTo, transitionType) 