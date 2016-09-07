""" This is Step 1. The user selects the pre- and post-contrast volumes 
	from which to construct a substraction map. TO-DO: Load test-case data,
	which will likely need to come from the TCIA module.
"""

from __main__ import qt, ctk, slicer

from BeersSingleStep import *
from Helper import *
from Editor import EditorWidget
from EditorLib import EditorLib

""" VolumeSelectStep inherits from BeersSingleStep, with itself inherits
	from a ctk workflow class. 
"""

class VolumeSelectStep(BeersSingleStep) :

	def __init__(self, stepid):

		""" This method creates a drop-down menu that includes the whole step.
			The description also acts as a tooltip for the button. There may be 
			some way to override this. The initialize method is presumably inherited
			from ctk.
		"""

		self.initialize( stepid )
		self.setName( '1. Volume Selection' )
		self.setDescription( 'Select the pre- and post-contrast volumes to calculate the subtraction map.' )

		self.__parent = super(VolumeSelectStep, self)

	def createUserInterface(self):

		""" This method uses qt to create a user interface. qMRMLNodeComboBox
			is a drop down menu for picking MRML files. MRML files are collected in
			a scene, hence .setMRMLscene.
		"""

		self.__layout = self.__parent.createUserInterface()
	 
		baselineScanLabel = qt.QLabel( 'Pre-contrast scan:' )
		self.__baselineVolumeSelector = slicer.qMRMLNodeComboBox()
		self.__baselineVolumeSelector.toolTip = "Choose the pre-contrast scan"
		self.__baselineVolumeSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
		self.__baselineVolumeSelector.setMRMLScene(slicer.mrmlScene)
		self.__baselineVolumeSelector.addEnabled = 0

		followupScanLabel = qt.QLabel( 'Post-contrast scan:' )
		self.__followupVolumeSelector = slicer.qMRMLNodeComboBox()
		self.__followupVolumeSelector.toolTip = "Choose the post-contrast scan"
		self.__followupVolumeSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
		self.__followupVolumeSelector.setMRMLScene(slicer.mrmlScene)
		self.__followupVolumeSelector.addEnabled = 0

		self.__layout.addRow( baselineScanLabel, self.__baselineVolumeSelector )
		self.__layout.addRow( followupScanLabel, self.__followupVolumeSelector )

		self.updateWidgetFromParameters(self.parameterNode())

		qt.QTimer.singleShot(0, self.killButton)

	def validate( self, desiredBranchId ):

		# validate is called whenever go to a different step
		self.__parent.validate( desiredBranchId )

		# Check here that the selectors are not empty / the same
		baseline = self.__baselineVolumeSelector.currentNode()
		followup = self.__followupVolumeSelector.currentNode()

		if baseline != None and followup != None:
			baselineID = baseline.GetID()
			followupID = followup.GetID()
			if baselineID != '' and followupID != '' and baselineID != followupID:
		
				pNode = self.parameterNode()
				pNode.SetParameter('baselineVolumeID', baselineID)
				pNode.SetParameter('followupVolumeID', followupID)

				self.__parent.validationSucceeded(desiredBranchId)
			else:
				self.__parent.validationFailed(desiredBranchId, 'Error','Please select distinctive baseline and followup volumes!')
		else:
			self.__parent.validationFailed(desiredBranchId, 'Error','Please select both baseline and followup volumes!')

	def onEntry(self, comingFrom, transitionType):

		super(VolumeSelectStep, self).onEntry(comingFrom, transitionType)

		self.updateWidgetFromParameters(self.parameterNode())
		
		pNode = self.parameterNode()
		pNode.SetParameter('currentStep', self.stepid)

		# A different attempt to get rid of the extra workflow button.
		qt.QTimer.singleShot(0, self.killButton)

	def onExit(self, goingTo, transitionType):   
		print slicer.util.findChildren('','EditColorFrame')
		super(BeersSingleStep, self).onExit(goingTo, transitionType) 

	def updateWidgetFromParameters(self, parameterNode):

		# To save parameters from step to step.
		baselineVolumeID = parameterNode.GetParameter('baselineVolumeID')
		followupVolumeID = parameterNode.GetParameter('followupVolumeID')
		if baselineVolumeID != None:
			self.__baselineVolumeSelector.setCurrentNode(Helper.getNodeByID(baselineVolumeID))
		if followupVolumeID != None:
			self.__followupVolumeSelector.setCurrentNode(Helper.getNodeByID(followupVolumeID))
