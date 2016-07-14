""" This is Step 2. The user has the option to register their pre- and post-contrast images
	using the module ExpertAutomatedRegistration. TO-DO: Add an option for BRAINSfit and
	add a progress bar.
"""

from __main__ import qt, ctk, slicer

from BeersSingleStep import *
from Helper import *

""" RegistrationStep inherits from BeersSingleStep, with itself inherits
	from a ctk workflow class. 
"""

class RegistrationStep( BeersSingleStep ) :
	
	def __init__( self, stepid ):

		""" This method creates a drop-down menu that includes the whole step.
		The description also acts as a tooltip for the button. There may be 
		some way to override this. The initialize method is inherited
		from ctk.
		"""

		self.initialize( stepid )
		self.setName( '2. Registration' )
		self.setDescription( """Please select your preferred method of registration. If you have already registered your images, or no registration is required, check the option "No Registration." Your post-contrast image will be registered to your pre-contrast image, and then resampled at the new registration. Be aware that many other modules in Slicer have more complex and/or customizable registration methods, should the methods in this step prove insufficient.
			""")

		self.__parent = super( RegistrationStep, self )

		self.__status = "Uncalled"
	
	def createUserInterface( self ):
		
		""" This method uses qt to create a user interface of radio buttons to select
		a registration method. Note that BSpline registration is so slow and memory-consuming
		as to at one point break Slicer. There is an option to run it with limited memory,
		but this may take prohibitively long.
		"""

		self.__layout = self.__parent.createUserInterface()

		# Moving/Fixed Image Registration Order Options

		OrderGroupBox = qt.QGroupBox()
		OrderGroupBox.setTitle('Registration Order')
		self.__layout.addRow(OrderGroupBox)

		OrderGroupBoxLayout = qt.QFormLayout(OrderGroupBox)

		self.__OrderRadio1 = qt.QRadioButton("Register pre-contrast to post-contrast.")
		self.__OrderRadio1.toolTip = "Your post-contrast image will be transformed."
		OrderGroupBoxLayout.addRow(self.__OrderRadio1)
		self.__OrderRadio1.setChecked(True)

		self.__OrderRadio2 = qt.QRadioButton("Register post-contrast to pre-contrast.")
		self.__OrderRadio2.toolTip = "Your pre-contrast image will be transformed."
		OrderGroupBoxLayout.addRow(self.__OrderRadio2)

		# # Resample/Transform Options

		# SamplingGroupBox = qt.QGroupBox()
		# SamplingGroupBox.setTitle('Resampling Options')
		# self.__layout.addRow(SamplingGroupBox)

		# SamplingGroupBoxLayout = qt.QFormLayout(SamplingGroupBox)

		# self.__SamplingRadio1 = qt.QRadioButton("Fix pre-contrast image; register post-contrast image.")
		# self.__SamplingRadio1.toolTip = "Your post-contrast image will be transformed."
		# SamplingGroupBoxLayout.addRow(self.__SamplingRadio1)
		# self.__radio1.setChecked(True)

		# self.__SamplingRadio2 = qt.QRadioButton("Fix post-contrast image; register pre-contrast image.")
		# self.__SamplingRadio2.toolTip = "Your pre-contrast image will be transformed."
		# SamplingGroupBoxLayout.addRow(self.__SamplingRadio2)

		# Registration Method Options

		RegistrationGroupBox = qt.QGroupBox()
		RegistrationGroupBox.setTitle('Registration Method')
		self.__layout.addRow(RegistrationGroupBox)

		RegistrationGroupBoxLayout = qt.QFormLayout(RegistrationGroupBox)

		self.__RegistrationRadio1 = qt.QRadioButton("No Registration")
		self.__RegistrationRadio1.toolTip = "Performs no registration."
		RegistrationGroupBoxLayout.addRow(self.__RegistrationRadio1)
		self.__RegistrationRadio1.setChecked(True)

		self.__RegistrationRadio2 = qt.QRadioButton("Rigid Registration (Fastest)")
		self.__RegistrationRadio2.toolTip = """Computes a rigid registration on the pre-contrast image with respect to the post-contrast image. This will likely be the fastest registration method"""
		RegistrationGroupBoxLayout.addRow(self.__RegistrationRadio2)

		self.__RegistrationRadio3 = qt.QRadioButton("Affine Registration")
		self.__RegistrationRadio3.toolTip = "Computes a rigid and affine registration on the pre-contrast image with respect to the post-contrast image."
		RegistrationGroupBoxLayout.addRow(self.__RegistrationRadio3)
		
		self.__RegistrationRadio4 = qt.QRadioButton("BSpline Registration (Slowest)")
		self.__RegistrationRadio4.toolTip = """Computes a BSpline Registration on the pre-contrast image with respect to the post-contrast image. This method is slowest and may be necessary for only severly distorted images."""
		RegistrationGroupBoxLayout.addRow(self.__RegistrationRadio4)

		self.__registrationButton = qt.QPushButton('Run registration')
		self.__registrationStatus = qt.QLabel('Register scans')
		self.__layout.addRow(self.__registrationStatus, self.__registrationButton)
		self.__registrationButton.connect('clicked()', self.onRegistrationRequest)

	def killButton(self):

		# ctk creates a useless final page button. This method gets rid of it.
		bl = slicer.util.findChildren(text='ReviewStep')
		if len(bl):
			bl[0].hide()

	def validate(self, desiredBranchId):

		""" This checks to make sure you are not currently registering an image, and
	  		throws an exception if so.
		"""

		self.__parent.validate( desiredBranchId )


		if self.__status == 'Uncalled':
			if self.__RegistrationRadio1.isChecked():
				self.__parent.validationSucceeded(desiredBranchId)
			else:
				self.__parent.validationFailed(desiredBranchId, 'Error','Please click \"Run Registration\" or select the \"No Registration\" option to continue.')
		elif self.__status == 'Completed':
			self.__parent.validationSucceeded(desiredBranchId)
		else:
			self.__parent.validationFailed(desiredBranchId, 'Error','Please wait until registration is completed.')

	def onEntry(self, comingFrom, transitionType):

		super(RegistrationStep, self).onEntry(comingFrom, transitionType)
		pNode = self.parameterNode()
		pNode.SetParameter('currentStep', self.stepid)
		Helper.SetBgFgVolumes(pNode.GetParameter('baselineVolumeID'),pNode.GetParameter('followupVolumeID'))

		# A different attempt to get rid of the extra workflow button.
		qt.QTimer.singleShot(0, self.killButton)

	def onExit(self, goingTo, transitionType):

		super(BeersSingleStep, self).onExit(goingTo, transitionType) 

	def onRegistrationRequest(self):

		""" This method makes a call to a different Slicer module, Expert Automated
			Registration. It is a command line interface (CLI) module that comes 
			pre-packaged with Slicer. It may be useful to develop a check, in case
			someone is using a version of slicer without this module. Other modules
			are avaliable too, such as BRAINSfit. Note that this registration method
			computes a transform, which is then applied to the followup volume in
			processRegistrationCompletion. TO-DO: Add a cancel button..
		"""
		if self.__RegistrationRadio1.isChecked():
			return
		else:
			pNode = self.parameterNode()

			#TO-DO: Find appropriate vtk subclass for non-BSpline transforms.
			self.__followupTransform = slicer.vtkMRMLBSplineTransformNode()
			slicer.mrmlScene.AddNode(self.__followupTransform)

			parameters = {}

			if self.__OrderRadio1.isChecked():
				fixedVolumeID = pNode.GetParameter('baselineVolumeID')
				movingVolumeID = pNode.GetParameter('followupVolumeID')
			else:
				fixedVolumeID = pNode.GetParameter('followupVolumeID')
				movingVolumeID = pNode.GetParameter('baselineVolumeID')

			fixedVolume = Helper.getNodeByID(fixedVolumeID)
			movingVolume = Helper.getNodeByID(movingVolumeID)

			parameters["fixedImage"] = fixedVolume
			parameters["movingImage"] = movingVolume
			parameters['saveTransform'] = self.__followupTransform
			parameters['resampledImage'] = movingVolume
			if self.__RegistrationRadio2.isChecked():
				parameters['registration'] = 'Rigid'
			if self.__RegistrationRadio3.isChecked():
				parameters['registration'] = 'Affine'
			if self.__RegistrationRadio4.isChecked():
				parameters['registration'] = 'BSpline'
				parameters['minimizeMemory'] = 'true'

			self.__cliNode = None
			self.__cliNode = slicer.cli.run(slicer.modules.expertautomatedregistration, self.__cliNode, parameters)

			# An event listener for the CLI. To-Do: Add a progress bar.
			self.__cliObserverTag = self.__cliNode.AddObserver('ModifiedEvent', self.processRegistrationCompletion)
			self.__registrationStatus.setText('Wait ...')
			self.__registrationButton.setEnabled(0)

	def processRegistrationCompletion(self, node, event):

		""" This updates the registration button with the CLI module's convenient status
			indicator. Upon completion, it applies the transform to the followup node.
			Furthermore, it sets the followup node to be the baseline node in the viewer.
			It also saves the transform node ID in the parameter node.
		"""

		self.__status = node.GetStatusString()
		self.__registrationStatus.setText('Registration ' + self.__status)

		if self.__status == 'Completed':
			self.__registrationButton.setEnabled(1)

			pNode = self.parameterNode()
			# followupNode = slicer.mrmlScene.GetNodeByID(pNode.GetParameter('followupVolumeID'))
			# followupNode.GetMatrixTransformFromNode(self.__followupTransform)
		
			Helper.SetBgFgVolumes(pNode.GetParameter('followupVolumeID'), pNode.GetParameter('baselineVolumeID'))

			pNode.SetParameter('followupTransformID', self.__followupTransform.GetID())

