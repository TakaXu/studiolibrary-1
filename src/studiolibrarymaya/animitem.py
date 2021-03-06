# Copyright 2019 by Kurt Rathjen. All Rights Reserved.
#
# This library is free software: you can redistribute it and/or modify it 
# under the terms of the GNU Lesser General Public License as published by 
# the Free Software Foundation, either version 3 of the License, or 
# (at your option) any later version. This library is distributed in the 
# hope that it will be useful, but WITHOUT ANY WARRANTY; without even the 
# implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU Lesser General Public License for more details.
# You should have received a copy of the GNU Lesser General Public
# License along with this library. If not, see <http://www.gnu.org/licenses/>.
"""
#---------------------------------------------------------------------------
# Saving an anim item
#---------------------------------------------------------------------------

from studiolibrarymaya import animitem

path = "/AnimLibrary/Characters/Malcolm/malcolm.anim"
objects = maya.cmds.ls(selection=True) or []

item = animitem.AnimItem(path)
item.save(objects=objects, startFrame=0, endFrame=200)

#---------------------------------------------------------------------------
# Loading an anim item
#---------------------------------------------------------------------------

from studiolibrarymaya import animitem

path = "/AnimLibrary/Characters/Malcolm/malcolm.anim"
objects = maya.cmds.ls(selection=True) or []
namespaces = []

item = animitem.AnimItem(path)
item.load(
    objects=objects,
    namespaces=namespaces,
    option="replaceCompletely",
    connect=False,
    currentTime=False,
)
"""

import os
import shutil
import logging

from studioqt import QtGui
from studioqt import QtWidgets

import studioqt
import studiolibrary
import studiolibrarymaya
import studiolibrary.widgets

from studiolibrarymaya import baseitem
from studiolibrarymaya import basecreatewidget

try:
    import mutils
    import mutils.gui
    import maya.cmds
except ImportError as error:
    print(error)


__all__ = [
    "AnimItem",
    "AnimItemError",
    "AnimCreateWidget",
]

logger = logging.getLogger(__name__)


class AnimItemError(Exception):

    """Base class for exceptions in this module."""


class ValidateAnimError(AnimItemError):

    """Raised when there is an invalid animation option"""


class AnimItem(baseitem.BaseItem):

    def __init__(self, *args, **kwargs):
        """
        Create a new instance of the anim item from the given path.

        :type path: str
        :type args: list
        :type kwargs: dict
        """
        baseitem.BaseItem.__init__(self, *args, **kwargs)

        self._items = []

        self.setTransferClass(mutils.Animation)
        self.setTransferBasename("")

    def info(self):
        """
        Get the info to display to user.
        
        :rtype: list[dict]
        """
        info = baseitem.BaseItem.info(self)

        startFrame = str(self.startFrame())
        endFrame = str(self.endFrame())

        info.insert(3, {"name": "Start frame", "value": startFrame})
        info.insert(4, {"name": "End frame", "value": endFrame})

        return info

    def loadOptions(self):
        """
        Get the options for the item.
        
        :rtype: list[dict]
        """
        startFrame = self.startFrame() or 0
        endFrame = self.endFrame() or 0

        return [
            {
                "name": "connect",
                "type": "bool",
                "default": False
            },
            {
                "name": "currentTime",
                "type": "bool",
                "default": True
            },
            {
                "name": "source",
                "type": "range",
                "default": [startFrame, endFrame],
                "persistent": False,
            },
            {
                "name": "option",
                "type": "enum",
                "default": "replace all",
                "items": ["replace", "replace all", "insert", "merge"],
            },
        ]

    def optionsChanged(self, **options):
        """
        Triggered when the user changes options.
        
        This method is not yet used. It will be used to change the state of 
        the options widget. For example the help image.
        
        :type options: dict
        """
        super(AnimItem, self).optionsChanged(**options)

        option = options.get("option")
        connect = options.get("connect")

        if option == "replace all":
            basename = "replaceCompletely"
            # self.ui.connectCheckBox.setEnabled(False)
        else:
            basename = option
            # self.ui.connectCheckBox.setEnabled(True)

        if connect and basename != "replaceCompletely":
            basename += "Connect"

        logger.debug(basename)

    def imageSequencePath(self):
        """
        Return the image sequence location for playing the animation preview.

        :rtype: str
        """
        return self.path() + "/sequence"

    def startFrame(self):
        """Return the start frame for the animation."""
        return self.transferObject().startFrame()

    def endFrame(self):
        """Return the end frame for the animation."""
        return self.transferObject().endFrame()

    @mutils.showWaitCursor
    def load(
        self,
        objects=None,
        namespaces=None,
        startFrame=None,
        source=None,
        option=None,
        connect=None,
        currentTime=False,
    ):
        """
        :type objects: list[str]
        :type namespaces: list[str]
        :type startFrame: bool
        :type source: int
        :type option: PasteOption or str
        :type connect: bool
        :type currentTime: bool
        :rtype: None
        """
        logger.info(u'Loading: {0}'.format(self.path()))

        objects = objects or []

        if option.lower() == "replace all":
            option = "replaceCompletely"

        if source and source != [0, 0]:
            sourceStart, sourceEnd = source
        else:
            sourceStart, sourceEnd = (None, None)

        if sourceStart is None:
            sourceStart = self.startFrame()

        if sourceEnd is None:
            sourceEnd = self.endFrame()

        self.transferObject().load(
            objects=objects,
            namespaces=namespaces,
            currentTime=currentTime,
            connect=connect,
            option=option,
            startFrame=startFrame,
            sourceTime=(sourceStart, sourceEnd)
        )

        logger.info(u'Loaded: {0}'.format(self.path()))

    def save(
        self,
        objects,
        path="",
        contents=None,
        iconPath="",
        fileType="",
        startFrame=None,
        endFrame=None,
        bakeConnected=False,
        metadata=None,
    ):
        """
        :type path: str
        :type objects: list[str] or None
        :type contents: list[str] or None
        :type iconPath: str
        :type startFrame: int or None
        :type endFrame: int or None
        :type fileType: str
        :type bakeConnected: bool
        :type metadata: None or dict

        :rtype: None
        """
        if path and not path.endswith(".anim"):
            path += ".anim"

        contents = contents or list()

        # Remove and create a new temp directory
        tempDir = mutils.TempDir("Transfer", clean=True)
        tempPath = tempDir.path() + "/transfer.anim"

        # Save the animation to the temp location
        anim = self.transferClass().fromObjects(objects)
        anim.updateMetadata(metadata)
        anim.save(
            tempPath,
            fileType=fileType,
            time=[startFrame, endFrame],
            bakeConnected=bakeConnected,
        )

        if iconPath:
            contents.append(iconPath)

        contents.extend(anim.paths())

        # Move the animation data to the given path using the base class
        super(AnimItem, self).save(path, contents=contents)


class AnimCreateWidget(basecreatewidget.BaseCreateWidget):

    def __init__(self, item=None, parent=None):
        """
        :type item: studiolibrary.LibraryItem
        :type parent: QtWidgets.QWidget
        """
        item = item or AnimItem()
        super(AnimCreateWidget, self).__init__(item, parent=parent)

        self._sequencePath = None

        start, end = (1, 100)

        try:
            start, end = mutils.currentFrameRange()
        except NameError as error:
            logger.exception(error)

        self.createSequenceWidget()

        validator = QtGui.QIntValidator(-50000000, 50000000, self)
        self.ui.endFrameEdit.setValidator(validator)
        self.ui.startFrameEdit.setValidator(validator)

        self.ui.endFrameEdit.setText(str(int(end)))
        self.ui.startFrameEdit.setText(str(int(start)))

        self.ui.byFrameEdit.setValidator(QtGui.QIntValidator(1, 1000, self))
        self.ui.frameRangeButton.clicked.connect(self.showFrameRangeMenu)

        settings = studiolibrarymaya.settings()

        byFrame = settings.get("byFrame")
        self.setByFrame(byFrame)

        fileType = settings.get("fileType")
        self.setFileType(fileType)

        self.ui.byFrameEdit.textChanged.connect(self.saveSettings)
        self.ui.fileTypeComboBox.currentIndexChanged.connect(self.saveSettings)

    def createSequenceWidget(self):
        """
        Create a sequence widget to replace the static thumbnail widget.

        :rtype: None
        """
        self.ui.sequenceWidget = studiolibrary.widgets.ImageSequenceWidget(self)
        self.ui.sequenceWidget.setStyleSheet(self.ui.thumbnailButton.styleSheet())
        self.ui.sequenceWidget.setToolTip(self.ui.thumbnailButton.toolTip())

        icon = studiolibrarymaya.resource().icon("thumbnail2")
        self.ui.sequenceWidget.setIcon(icon)

        self.ui.thumbnailFrame.layout().insertWidget(0, self.ui.sequenceWidget)
        self.ui.thumbnailButton.hide()
        self.ui.thumbnailButton = self.ui.sequenceWidget

        self.ui.sequenceWidget.clicked.connect(self.thumbnailCapture)

    def sequencePath(self):
        """
        Return the playblast path.

        :rtype: str
        """
        return self._sequencePath

    def setSequencePath(self, path):
        """
        Set the disk location for the image sequence to be saved.

        :type path: str
        :rtype: None
        """
        self._sequencePath = path
        self.ui.sequenceWidget.setDirname(os.path.dirname(path))

    def startFrame(self):
        """
        Return the start frame that will be exported.

        :rtype: int | None
        """
        try:
            return int(float(str(self.ui.startFrameEdit.text()).strip()))
        except ValueError:
            return None

    def endFrame(self):
        """
        Return the end frame that will be exported.

        :rtype: int | None
        """
        try:
            return int(float(str(self.ui.endFrameEdit.text()).strip()))
        except ValueError:
            return None

    def duration(self):
        """
        Return the duration of the animation that will be exported.

        :rtype: int
        """
        return self.endFrame() - self.startFrame()

    def byFrame(self):
        """
        Return the by frame for the playblast.

        :rtype: int
        """
        return int(float(self.ui.byFrameEdit.text()))

    def setByFrame(self, byFrame):
        """
        Set the by frame for the playblast.

        :type byFrame: int or str
        :rtype: None
        """
        self.ui.byFrameEdit.setText(str(byFrame))

    def fileType(self):
        """
        Return the file type for the animation.

        :rtype: str
        """
        return self.ui.fileTypeComboBox.currentText()

    def setFileType(self, fileType):
        """
        Set the file type for the animation.

        :type fileType: str
        """
        fileTypeIndex = self.ui.fileTypeComboBox.findText(fileType)
        if fileTypeIndex:
            self.ui.fileTypeComboBox.setCurrentIndex(fileTypeIndex)

    def settings(self):
        """
        Overriding this method to add support for saving the byFrame and type.
        
        :rtype: dict 
        """
        settings = super(AnimCreateWidget, self).settings()

        settings["byFrame"] = self.byFrame()
        settings["fileType"] = self.fileType()

        return settings

    def showFrameRangeMenu(self):
        """
        Show the frame range menu at the current cursor location.

        :rtype: None
        """
        action = mutils.gui.showFrameRangeMenu()
        if action:
            self.setFrameRange(action.frameRange())

    def setFrameRange(self, frameRange):
        """
        Set the frame range for the animation to be exported.

        :type frameRange: (int, int)
        """
        start, end = frameRange

        if start == end:
            end += 1

        self.setStartFrame(start)
        self.setEndFrame(end)

    def setEndFrame(self, frame):
        """
        Set the end frame range for the animation to be exported.

        :type frame: int or str
        """
        self.ui.endFrameEdit.setText(str(int(frame)))

    def setStartFrame(self, frame):
        """
        Set the start frame range for the animation to be exported.

        :type frame: int or str
        """
        self.ui.startFrameEdit.setText(str(int(frame)))

    def showByFrameDialog(self):
        """
        Show the by frame dialog.

        :rtype: None
        """
        text = 'To help speed up the playblast you can set the "by frame" ' \
               'to a number greater than 1. For example if the "by frame" ' \
               'is set to 2 it will playblast every second frame.'

        if self.duration() > 100 and self.byFrame() == 1:

            buttons = QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel

            result = studiolibrary.widgets.MessageBox.question(
                self.libraryWindow(),
                title="Anim Item Tip",
                text=text,
                buttons=buttons,
                enableDontShowCheckBox=True,
            )

            if result != QtWidgets.QMessageBox.Ok:
                raise Exception("Canceled!")

    def _thumbnailCaptured(self, playblastPath):
        """
        Triggered when the user captures a thumbnail/playblast.

        :type playblastPath: str
        :rtype: None
        """
        thumbnailPath = mutils.gui.tempThumbnailPath()
        shutil.copyfile(playblastPath, thumbnailPath)

        self.setIconPath(thumbnailPath)
        self.setSequencePath(playblastPath)

    def thumbnailCapture(self):
        """
        :raise: AnimItemError
        """
        startFrame, endFrame = mutils.selectedFrameRange()
        if startFrame == endFrame:
            self.validateFrameRange()
            endFrame = self.endFrame()
            startFrame = self.startFrame()

        # Ignore the by frame dialog when the control modifier is pressed.
        if not studioqt.isControlModifier():
            self.showByFrameDialog()

        try:
            step = self.byFrame()
            playblastPath = mutils.gui.tempPlayblastPath()

            mutils.gui.thumbnailCapture(
                path=playblastPath,
                startFrame=startFrame,
                endFrame=endFrame,
                step=step,
                clearCache=True,
                captured=self._thumbnailCaptured,
            )

        except Exception as e:
            title = "Error while capturing thumbnail"
            QtWidgets.QMessageBox.critical(self.libraryWindow(), title, str(e))
            raise

    def validateFrameRange(self):
        """
        :raise: ValidateAnimationError
        """
        if self.startFrame() is None or self.endFrame() is None:
            msg = "Please choose a start frame and an end frame."
            raise ValidateAnimError(msg)

    def save(self, objects, path, iconPath, metadata):
        """
        :type objects: list[str]
        :type path: str
        :type iconPath: str
        :type metadata: None or dict
        :rtype: None
        """
        contents = None
        endFrame = self.endFrame()
        startFrame = self.startFrame()
        fileType = self.ui.fileTypeComboBox.currentText()
        bakeConnected = int(self.ui.bakeCheckBox.isChecked())

        item = self.item()
        iconPath = self.iconPath()

        sequencePath = self.sequencePath()
        if sequencePath:
            contents = [os.path.dirname(sequencePath)]

        item.save(
            path=path,
            objects=objects,
            contents=contents,
            iconPath=iconPath,
            fileType=fileType,
            endFrame=endFrame,
            startFrame=startFrame,
            bakeConnected=bakeConnected,
            metadata=metadata
        )


# Register the anim item to the Studio Library
iconPath = studiolibrarymaya.resource().get("icons", "animation.png")

AnimItem.Extensions = [".anim"]
AnimItem.MenuName = "Animation"
AnimItem.MenuIconPath = iconPath
AnimItem.TypeIconPath = iconPath
AnimItem.CreateWidgetClass = AnimCreateWidget

studiolibrary.registerItem(AnimItem)
