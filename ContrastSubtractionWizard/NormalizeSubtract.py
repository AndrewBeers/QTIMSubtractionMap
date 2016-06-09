""" This is Step 3. The user has the option to normalize intensity values
	across pre- and post-contrast images before subtracting them.
"""

from __main__ import qt, ctk, slicer

from BeersSingleStep import *
from Helper import *

""" NormalizeSubtractStep inherits from BeersSingleStep, with itself inherits
	from a ctk workflow class. 
"""

class NormalizeSubtractStep( BeersSingleStep ) :

	def __init__( self, stepid ):

		""" This method creates a drop-down menu that includes the whole step.
			The description also acts as a tooltip for the button. There may be 
			some way to override this. The initialize method is inherited
			from ctk.
		"""

		self.initialize( stepid )
		self.setName( '3. Normalization and Subtraction' )
		self.setDescription( 'You have the option to normalize the intensities between your images before you subtract them. This may lead to better contrast in the resulting image. The method below divides both images by the standard deviation of their intensities in order to get a measure of relative intensity. Changes in intensity as rendered in the scene may only be slight.' )

		self.__status = 'uncalled'
		self.__parent = super( NormalizeSubtractStep, self )

	def createUserInterface( self ):

		""" As of now, this user interface is fairly simple. If there are other methods of
			normalization, they could be added here.
		"""

		self.__layout = self.__parent.createUserInterface()

		NormSubtractGroupBox = qt.QGroupBox()
		NormSubtractGroupBox.setTitle('Normalization and Subtraction Methods')
		self.__layout.addRow(NormSubtractGroupBox)

		NormSubtractGroupBoxLayout = qt.QFormLayout(NormSubtractGroupBox)

		self.__normalizationButton = qt.QPushButton('Run Gaussian Normalization')
		NormSubtractGroupBoxLayout.addRow(self.__normalizationButton)

		self.__subtractionButton = qt.QPushButton('Run Subtraction Algorithm')
		NormSubtractGroupBoxLayout.addRow(self.__subtractionButton)

		self.__normalizationButton.connect('clicked()', self.onNormalizationRequest)
		self.__subtractionButton.connect('clicked()', self.onSubtractionRequest)


	def killButton(self):

		# ctk creates a useless final page button. This method gets rid of it.
		bl = slicer.util.findChildren(text='ReviewStep')
		if len(bl):
			bl[0].hide()

	def validate( self, desiredBranchId ):

		# Does not validate while subtraction is in process, or has not yet occured.
		if self.__status != 'Completed':
			self.__parent.validationFailed(desiredBranchId, 'Error','You must have completed an image subtraction before moving to the next step.')
		else:
			self.__parent.validationSucceeded(desiredBranchId)

	def onEntry(self, comingFrom, transitionType):

		super(NormalizeSubtractStep, self).onEntry(comingFrom, transitionType)

		self.__normalizationButton.setText('Run Gaussian Normalization')
		self.__subtractionButton.setText('Run Subtraction Algorithm')
		self.__normalizationButton.setEnabled(1)
		self.__subtractionButton.setEnabled(1)
		self.__status = 'uncalled'
		pNode = self.parameterNode()
		pNode.SetParameter('currentStep', self.stepid)
		Helper.SetBgFgVolumes(pNode.GetParameter('baselineVolumeID'),pNode.GetParameter('followupVolumeID'))
		
		qt.QTimer.singleShot(0, self.killButton)

	def onExit(self, goingTo, transitionType):

		# Some work must be done to call the ROI interface upon exiting.
		self.ROIPrep() 
		super(BeersSingleStep, self).onExit(goingTo, transitionType) 

	def ROIPrep(self):

		""" vtk, the image analysis library, and Slicer use different coordinate
			systems: IJK and RAS, respectively. This prep calculates a simple matrix 
			transformation on a ROI transform node to be used in the next step.
		"""

		pNode = self.parameterNode()

		subtractVolume = Helper.getNodeByID(pNode.GetParameter('subtractVolumeID'))
		roiTransformID = pNode.GetParameter('roiTransformID')
		roiTransformNode = None

		if roiTransformID != '':
			roiTransformNode = Helper.getNodeByID(roiTransformID)
		else:
			roiTransformNode = slicer.vtkMRMLLinearTransformNode()
			slicer.mrmlScene.AddNode(roiTransformNode)
			pNode.SetParameter('roiTransformID', roiTransformNode.GetID())

		# TO-DO: Understand the precise math behind this section of code..
		dm = vtk.vtkMatrix4x4()
		subtractVolume.GetIJKToRASDirectionMatrix(dm)
		dm.SetElement(0,3,0)
		dm.SetElement(1,3,0)
		dm.SetElement(2,3,0)
		dm.SetElement(0,0,abs(dm.GetElement(0,0)))
		dm.SetElement(1,1,abs(dm.GetElement(1,1)))
		dm.SetElement(2,2,abs(dm.GetElement(2,2)))
		roiTransformNode.SetAndObserveMatrixTransformToParent(dm)

	def onSubtractionRequest(self):

		""" This method subtracts two images pixel-for-pixel using Slicer's 
			subtractscalarvolumes module. It apparently can deal with differently
			sized images. A new volume is created and displayed, subtractVolume.
		"""

		pNode = self.parameterNode()
		baselineVolumeID = pNode.GetParameter('baselineVolumeID')
		followupVolumeID = pNode.GetParameter('followupVolumeID')
		followupVolume = Helper.getNodeByID(followupVolumeID)
		baselineVolume = Helper.getNodeByID(baselineVolumeID)

		subtractVolume = slicer.vtkMRMLScalarVolumeNode()
		subtractVolume.SetScene(slicer.mrmlScene)
		subtractVolume.SetName(Helper.getNodeByID(baselineVolumeID).GetName() + '_subtraction')
		slicer.mrmlScene.AddNode(subtractVolume)
		pNode.SetParameter('subtractVolumeID', subtractVolume.GetID())

		# TO-D0: Understand the math behind interpolation order in image subtraction
		parameters = {}
		parameters["inputVolume1"] = followupVolume
		parameters["inputVolume2"] = baselineVolume
		parameters['outputVolume'] = subtractVolume
		parameters['order'] = '1'

		self.__cliNode = None
		self.__cliNode = slicer.cli.run(slicer.modules.subtractscalarvolumes, self.__cliNode, parameters)

		# An event listener for the CLI. To-Do: Add a progress bar.
		self.__cliObserverTag = self.__cliNode.AddObserver('ModifiedEvent', self.processSubtractionCompletion)
		self.__subtractionButton.setText('Subtraction running...')
		self.__subtractionButton.setEnabled(0)


	def processSubtractionCompletion(self, node, event):

		""" This updates the registration button with the CLI module's convenient status
			indicator.
		"""

		self.__status = node.GetStatusString()

		if self.__status == 'Completed':
			self.__subtractionButton.setText('Subtraction completed!')

	def onNormalizationRequest(self):

		""" This method uses vtk algorithms to perform simple image calculations. Slicer 
			images are stored in vtkImageData format, making it difficult to edit them
			without using vtk. Here, vtkImageShiftScale and vtkImageHistogramStatistics
			are used to generate max, standard deviation, and simple multiplication. Currently,
			I create an instance for both baseline and followup; a better understanding
			of vtk may lead me to consolidate them into one instance later.
		"""

		self.__normalizationButton.setEnabled(0)
		self.__normalizationButton.setText('Normalization running...')

		pNode = self.parameterNode()

		baselineLabel = pNode.GetParameter('baselineVolumeID')
		followupLabel = pNode.GetParameter('followupVolumeID')

		baselineNode = slicer.mrmlScene.GetNodeByID(baselineLabel)
		followupNode = slicer.mrmlScene.GetNodeByID(followupLabel)

		baselineImage = baselineNode.GetImageData()
		followupImage = followupNode.GetImageData()

		imageArray = [baselineImage, followupImage]
		stdArray = [0,0]
		maxArray = [0,0]
		vtkScaleArray = [vtk.vtkImageShiftScale(), vtk.vtkImageShiftScale()]
		vtkStatsArray = [vtk.vtkImageHistogramStatistics(), vtk.vtkImageHistogramStatistics()]

		# Descriptive statistics are retrieved.
		for i in [0,1]:
			vtkStatsArray[i].SetInputData(imageArray[i])
			vtkStatsArray[i].Update()
			maxArray[i] = vtkStatsArray[i].GetMaximum()
			stdArray[i] = vtkStatsArray[i].GetStandardDeviation()

		# Values are rescaled to the highest intensity value from both images.
		CommonMax = maxArray.index(max(maxArray))

		# Image scalar multiplication is perfored to normalize the two images.
		for i in [0,1]:
			vtkScaleArray[i].SetInputData(imageArray[i])
			vtkScaleArray[i].SetOutputScalarTypeToInt()
			scalar = float(stdArray[CommonMax]) / float(stdArray[i])
			vtkScaleArray[i].SetScale(scalar)
			vtkScaleArray[i].Update()
			imageArray[i] = vtkScaleArray[i].GetOutput()

		# Node image data is replaced. The image with the higher max intensity effectively does not change.
		baselineNode.SetAndObserveImageData(imageArray[0])
		followupNode.SetAndObserveImageData(imageArray[1])
		self.__normalizationButton.setText('Normalization complete!')
