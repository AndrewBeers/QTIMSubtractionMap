""" This is Step 4. The user selects a ROI and subtracts the two images.
	Much of this step is copied from ChangeTracker, located at 
	https://github.com/fedorov/ChangeTrackerPy. This step can be
	excessively slow, and at one point crashed Slicer; more investigation
	is needed.
"""

from __main__ import qt, ctk, slicer

from BeersSingleStep import *
from Helper import *
import PythonQt

""" ROIStep inherits from BeersSingleStep, with itself inherits
	from a ctk workflow class. PythonQT is required for this step
	in order to get the ROI selector widget.
"""

class ROIStep( BeersSingleStep ) :

	def __init__( self, stepid ):

		""" This method creates a drop-down menu that includes the whole step.
		The description also acts as a tooltip for the button. There may be 
		some way to override this. The initialize method is inherited
		from ctk.
		"""

		self.initialize( stepid )
		self.setName( '4. Define ROI' )
		self.setDescription( 'Select a region of interest, either with a pre-defined ROI or with the interactive tools below.' )

		self.__parent = super( ROIStep, self )

		self.__vrDisplayNode = None

		self.__roiTransformNode = None
		self.__baselineVolume = None

		self.__roi = None
		self.__roiObserverTag = None

	def createUserInterface( self ):

		""" This UI allows you to either select a predefined ROI via the 
			vtkMRMLAnnotationROINode feature, or to specify your own using
			PythonQt's qMRMLAnnotationROIWidget. That creates a fairly large
			box with 3 sliders to adjust your ROI in three dimensions. There is
			also a ROI drow-down selector for those who have a pre-loaded ROI.
		"""

		self.__layout = self.__parent.createUserInterface()

		roiLabel = qt.QLabel( 'Select ROI:' )
		self.__roiSelector = slicer.qMRMLNodeComboBox()
		self.__roiSelector.nodeTypes = ['vtkMRMLAnnotationROINode']
		self.__roiSelector.toolTip = "ROI defining the structure of interest"
		self.__roiSelector.setMRMLScene(slicer.mrmlScene)
		self.__roiSelector.addEnabled = 1

		self.__layout.addRow( roiLabel, self.__roiSelector )

		self.__roiSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onROIChanged)

		voiGroupBox = qt.QGroupBox()
		voiGroupBox.setTitle( 'Define ROI' )
		self.__layout.addRow( voiGroupBox )

		voiGroupBoxLayout = qt.QFormLayout( voiGroupBox )

		# PythonQt has a pre-configured ROI widget. Useful!
		self.__roiWidget = PythonQt.qSlicerAnnotationsModuleWidgets.qMRMLAnnotationROIWidget()
		voiGroupBoxLayout.addRow( self.__roiWidget )
		self.__roiWidget.setEnabled(1)

		# Intialize Volume Rendering...
		self.__vrLogic = slicer.modules.volumerendering.logic()

		qt.QTimer.singleShot(0, self.killButton)

	def killButton(self):

		# ctk creates a useless final page button. This method gets rid of it.
		bl = slicer.util.findChildren(text='ReviewStep')
		if len(bl):
			bl[0].hide()

	def onROIChanged(self):

		""" This method accounts for changing ROI nodes entirely, rather than the
			parameters of individual nodes.
		"""

		roi = self.__roiSelector.currentNode()

		if roi != None:
			self.__roi = roi
	
			pNode = self.parameterNode()

			self.InitVRDisplayNode()

			self.__vrDisplayNode.SetAndObserveROINodeID(roi.GetID())
			self.__vrDisplayNode.SetCroppingEnabled(1)
			self.__vrDisplayNode.VisibilityOn()

			roi.SetAndObserveTransformNodeID(self.__roiTransformNode.GetID())

			# Removes unneeded observers, freeing running time.
			if self.__roiObserverTag != None:
				self.__roi.RemoveObserver(self.__roiObserverTag)

			self.__roiObserverTag = self.__roi.AddObserver('ModifiedEvent', self.processROIEvents)

			roi.SetInteractiveMode(1)

			self.__roiWidget.setMRMLAnnotationROINode(roi)
			self.__roi.SetDisplayVisibility(1)
	 
	def processROIEvents(self,node,event):
		""" A rather repetitive step that does the hard work of computing
			IJK boundaries in vtk and RAS boundaries in Slicer. Also adjusts
			the opacity of the volume rendering node.
		"""

		# Get the IJK bounding box of the voxels inside ROI.
		roiCenter = [0,0,0]
		roiRadius = [0,0,0]

		# Note that these methods modify roiCenter and roiRadius.
		self.__roi.GetXYZ(roiCenter)
		self.__roi.GetRadiusXYZ(roiRadius)

		# TO-DO: Understand coordinate changes being performed.
		roiCorner1 = [roiCenter[0]+roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]+roiRadius[2],1]
		roiCorner2 = [roiCenter[0]+roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]-roiRadius[2],1]
		roiCorner3 = [roiCenter[0]+roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]+roiRadius[2],1]
		roiCorner4 = [roiCenter[0]+roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]-roiRadius[2],1]
		roiCorner5 = [roiCenter[0]-roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]+roiRadius[2],1]
		roiCorner6 = [roiCenter[0]-roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]-roiRadius[2],1]
		roiCorner7 = [roiCenter[0]-roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]+roiRadius[2],1]
		roiCorner8 = [roiCenter[0]-roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]-roiRadius[2],1]

		ras2ijk = vtk.vtkMatrix4x4()
		self.__subtractVolume.GetRASToIJKMatrix(ras2ijk)

		roiCorner1ijk = ras2ijk.MultiplyPoint(roiCorner1)
		roiCorner2ijk = ras2ijk.MultiplyPoint(roiCorner2)
		roiCorner3ijk = ras2ijk.MultiplyPoint(roiCorner3)
		roiCorner4ijk = ras2ijk.MultiplyPoint(roiCorner4)
		roiCorner5ijk = ras2ijk.MultiplyPoint(roiCorner5)
		roiCorner6ijk = ras2ijk.MultiplyPoint(roiCorner6)
		roiCorner7ijk = ras2ijk.MultiplyPoint(roiCorner7)
		roiCorner8ijk = ras2ijk.MultiplyPoint(roiCorner8)

		lowerIJK = [0, 0, 0]
		upperIJK = [0, 0, 0]

		lowerIJK[0] = min(roiCorner1ijk[0],roiCorner2ijk[0],roiCorner3ijk[0],roiCorner4ijk[0],roiCorner5ijk[0],roiCorner6ijk[0],roiCorner7ijk[0],roiCorner8ijk[0])
		lowerIJK[1] = min(roiCorner1ijk[1],roiCorner2ijk[1],roiCorner3ijk[1],roiCorner4ijk[1],roiCorner5ijk[1],roiCorner6ijk[1],roiCorner7ijk[1],roiCorner8ijk[1])
		lowerIJK[2] = min(roiCorner1ijk[2],roiCorner2ijk[2],roiCorner3ijk[2],roiCorner4ijk[2],roiCorner5ijk[2],roiCorner6ijk[2],roiCorner7ijk[2],roiCorner8ijk[2])

		upperIJK[0] = max(roiCorner1ijk[0],roiCorner2ijk[0],roiCorner3ijk[0],roiCorner4ijk[0],roiCorner5ijk[0],roiCorner6ijk[0],roiCorner7ijk[0],roiCorner8ijk[0])
		upperIJK[1] = max(roiCorner1ijk[1],roiCorner2ijk[1],roiCorner3ijk[1],roiCorner4ijk[1],roiCorner5ijk[1],roiCorner6ijk[1],roiCorner7ijk[1],roiCorner8ijk[1])
		upperIJK[2] = max(roiCorner1ijk[2],roiCorner2ijk[2],roiCorner3ijk[2],roiCorner4ijk[2],roiCorner5ijk[2],roiCorner6ijk[2],roiCorner7ijk[2],roiCorner8ijk[2])

		# All of this ijk work is needed for using vtk to compute a sub-region.
		image = self.__subtractVolume.GetImageData()
		clipper = vtk.vtkImageClip()
		clipper.ClipDataOn()
		clipper.SetOutputWholeExtent(int(lowerIJK[0]),int(upperIJK[0]),int(lowerIJK[1]),int(upperIJK[1]),int(lowerIJK[2]),int(upperIJK[2]))
		if vtk.VTK_MAJOR_VERSION <= 5:
			clipper.SetInput(image)
		else:
			clipper.SetInputData(image)
		clipper.Update()
		roiImageRegion = clipper.GetOutput()

		# Opacity thresholds are constantly adjusted to the range of pixels within the ROI.
		intRange = roiImageRegion.GetScalarRange()
		lThresh = 0.4*(intRange[0]+intRange[1])
		uThresh = intRange[1]

		self.__vrOpacityMap.RemoveAllPoints()
		self.__vrOpacityMap.AddPoint(0,0)
		self.__vrOpacityMap.AddPoint(lThresh-1,0)
		self.__vrOpacityMap.AddPoint(lThresh,1)
		self.__vrOpacityMap.AddPoint(uThresh,1)
		self.__vrOpacityMap.AddPoint(uThresh+1,0)

		# Center the camera on the new ROI. Author of ChangeTracker suggested errors in this method.
		camera = slicer.mrmlScene.GetNodeByID('vtkMRMLCameraNode1')
		camera.SetFocalPoint(roiCenter)

	def validate( self, desiredBranchId ):

		# Makes sure there actually is a ROI...
		roi = self.__roiSelector.currentNode()
		if roi == None:
			self.__parent.validationFailed(desiredBranchId, 'Error', 'Please define ROI!')
			
		self.__parent.validationSucceeded(desiredBranchId)

	def onEntry(self,comingFrom,transitionType):

		""" This method calls most other methods in this function to initialize the ROI
			wizard. This step in particular applies the ROI IJK/RAS coordinate transform
			calculated in the previous step and checks for any pre-existing ROIs. Also
			intializes the volume-rendering node.
		"""

		super(ROIStep, self).onEntry(comingFrom, transitionType)

		# I believe this changes the layout to four-up; will check.
		lm = slicer.app.layoutManager()
		lm.setLayout(3)
		pNode = self.parameterNode()
		Helper.SetLabelVolume(None)
		self.__subtractVolume = slicer.mrmlScene.GetNodeByID(pNode.GetParameter('subtractVolumeID'))
		Helper.SetBgFgVolumes(pNode.GetParameter('subtractVolumeID'),'')

		# Apply the transform node created in the previous step.
		roiTfmNodeID = pNode.GetParameter('roiTransformID')
		if roiTfmNodeID != '':
			self.__roiTransformNode = Helper.getNodeByID(roiTfmNodeID)
		else:
			Helper.Error('Internal error! Error code CT-S2-NRT, please report!')

		# If a ROI exists, grab it. Note that this function calls onROIChanged()
		self.updateWidgetFromParameterNode(pNode)

		# Note that this clause initializes volume rendering.
		if self.__roi != None:
			self.__roi.SetDisplayVisibility(1)
			self.InitVRDisplayNode()

		pNode.SetParameter('currentStep', self.stepid)
		
		qt.QTimer.singleShot(0, self.killButton)

	def onExit(self, goingTo, transitionType):

		# Does a great deal of work to prepare for the segmentation step.
		self.ThresholdPrep()

		if self.__roi != None:
			self.__roi.RemoveObserver(self.__roiObserverTag)
			self.__roi.SetDisplayVisibility(0)
		
		pNode = self.parameterNode()

		if self.__vrDisplayNode != None:
			# self.__vrDisplayNode.VisibilityOff()
			pNode.SetParameter('vrDisplayNodeID', self.__vrDisplayNode.GetID())

		pNode.SetParameter('roiNodeID', self.__roiSelector.currentNode().GetID())

		super(ROIStep, self).onExit(goingTo, transitionType)

	def updateWidgetFromParameterNode(self, parameterNode):

		""" Effectively creates the ROI node upon entry, and then uses onROIChanged
			to calculate its intial position.
		"""

		roiNodeID = parameterNode.GetParameter('roiNodeID')

		if roiNodeID != '':
			self.__roi = slicer.mrmlScene.GetNodeByID(roiNodeID)
			self.__roiSelector.setCurrentNode(Helper.getNodeByID(self.__roi.GetID()))
		else:
			roi = slicer.vtkMRMLAnnotationROINode()
			roi.Initialize(slicer.mrmlScene)
			parameterNode.SetParameter('roiNodeID', roi.GetID())
			self.__roiSelector.setCurrentNode(roi)
		
		self.onROIChanged()
		
	def ThresholdPrep(self):

		""" This method prepares for the following segmentation/thresholding
			step. It accomplishes a few things. It uses the cropvolume Slicer
			module to create a new, ROI-only node. It then creates a label volume
			and initializes threholds variables for the next step.
		"""

		# Crop volume to ROI.
		pNode = self.parameterNode()
		cropVolumeNode = slicer.vtkMRMLCropVolumeParametersNode()
		cropVolumeNode.SetScene(slicer.mrmlScene)
		cropVolumeNode.SetName('T1_Contrast_CropVolume_node')
		cropVolumeNode.SetIsotropicResampling(True)
		cropVolumeNode.SetSpacingScalingConst(0.5)
		slicer.mrmlScene.AddNode(cropVolumeNode)

		cropVolumeNode.SetInputVolumeNodeID(pNode.GetParameter('subtractVolumeID'))
		cropVolumeNode.SetROINodeID(pNode.GetParameter('roiNodeID'))

		cropVolumeLogic = slicer.modules.cropvolume.logic()
		cropVolumeLogic.Apply(cropVolumeNode)

		baselineVolumeID = pNode.GetParameter('baselineVolumeID')
		followupVolumeID = pNode.GetParameter('followupVolumeID')

		followupVolume = Helper.getNodeByID(followupVolumeID)
		baselineVolume = Helper.getNodeByID(baselineVolumeID)

		outputVolume = slicer.mrmlScene.GetNodeByID(cropVolumeNode.GetOutputVolumeNodeID())
		outputVolume.SetName(baselineVolume.getName() + '_subtraction_roi')
		pNode.SetParameter('croppedSubtractVolumeID',cropVolumeNode.GetOutputVolumeNodeID())

		# Get starting threshold parameters.
		roiSegmentationID = pNode.GetParameter('croppedSubtractVolumeSegmentationID') 
		if roiSegmentationID == '':
			roiRange = outputVolume.GetImageData().GetScalarRange()

			thresholdParameter = str(0.5*(roiRange[0]+roiRange[1]))+','+str(roiRange[1])
			pNode.SetParameter('thresholdRange', thresholdParameter)

		# Create a label node for segmentation.
		vl = slicer.modules.volumes.logic()
		roiSegmentation = vl.CreateLabelVolume(slicer.mrmlScene, outputVolume, baselineVolumeID.getName() + 'subtraction_annotation')
		pNode.SetParameter('croppedSubtractVolumeSegmentationID', roiSegmentation.GetID())

	def InitVRDisplayNode(self):

		"""	This method calls a series of steps necessary to initailizing a volume 
			rendering node with an ROI.
		"""

		if self.__vrDisplayNode == None:
			pNode = self.parameterNode()
			vrNodeID = pNode.GetParameter('vrDisplayNodeID')
			if vrNodeID == '':
				self.__vrDisplayNode = self.__vrLogic.CreateVolumeRenderingDisplayNode()
				slicer.mrmlScene.AddNode(self.__vrDisplayNode)

				# Documentation on UnRegister is scant so far.
				self.__vrDisplayNode.UnRegister(self.__vrLogic) 

				v = slicer.mrmlScene.GetNodeByID(self.parameterNode().GetParameter('subtractVolumeID'))
				Helper.InitVRDisplayNode(self.__vrDisplayNode, v.GetID(), self.__roi.GetID())
				v.AddAndObserveDisplayNodeID(self.__vrDisplayNode.GetID())
			else:
				self.__vrDisplayNode = slicer.mrmlScene.GetNodeByID(vrNodeID)

		# This is a bit messy.
		viewNode = slicer.util.getNode('vtkMRMLViewNode1')

		self.__vrDisplayNode.AddViewNodeID(viewNode.GetID())
		
		self.__vrLogic.CopyDisplayToVolumeRenderingDisplayNode(self.__vrDisplayNode)

		self.__vrOpacityMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetScalarOpacity()
		self.__vrColorMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetRGBTransferFunction()

		# Renders in yellow, like the label map in the next steps.
		self.__vrColorMap.RemoveAllPoints()
		self.__vrColorMap.AddRGBPoint(0, 0.8, 0.8, 0)
		self.__vrColorMap.AddRGBPoint(500, 0.8, 0.8, 0)