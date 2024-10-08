# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2023 Richard Frangenberg
# Copyright (C) 2023 Prism Software GmbH
#
# Licensed under GNU LGPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.


import os
import sys

if sys.version[0] == "3":
    import collections.abc as collections
else:
    import collections

from qtpy.QtCore import *
from qtpy.QtGui import *
from qtpy.QtWidgets import *

if eval(os.getenv("PRISM_DEBUG", "False")):
    try:
        del sys.modules["PrismWidgets"]
    except:
        pass

from PrismUtils import PrismWidgets
from PrismUtils.Decorators import err_catcher
from UserInterfaces import ItemList_ui


class ItemList(QDialog, ItemList_ui.Ui_dlg_ItemList):
    def __init__(self, core, entities=None, mode="passes"):
        QDialog.__init__(self)
        self.setupUi(self)

        self.core = core
        self.entities = entities
        self.mode = mode

        self.tw_steps.setColumnCount(2)
        self.tw_steps.setHorizontalHeaderLabels(["Abbreviation", "Department"])
        self.tw_steps.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        if (
            mode != "departments"
            or (
                self.entities[0]["type"] == "asset"
                and self.core.compareVersions(self.core.projectVersion, "v1.2.1.6")
                == "lower"
            )
        ):
            self.chb_category.setVisible(False)
        else:
            self.chb_category.setChecked(False)

        self.buttonBox.buttons()[0].setText("Create")
        self.buttonBox.clicked.connect(self.buttonboxClicked)

        self.btext = "Next"
        if self.entities and (self.mode == "departments" or self.core.appPlugin.pluginName != "Standalone"):
            self.b_next = self.buttonBox.addButton(self.btext, QDialogButtonBox.AcceptRole)
            if self.mode == "tasks":
                toolTip = "Create tasks and create a new scene from the current scene"
            else:
                toolTip = "Create department and open category dialog"
            
            self.b_next.setToolTip(toolTip)
            self.b_next.setEnabled(False)
            iconPath = os.path.join(
                self.core.prismRoot, "Scripts", "UserInterfacesPrism", "arrow_right.png"
            )
            icon = self.core.media.getColoredIcon(iconPath)
            self.b_next.setIcon(icon)

            if self.mode == "departments":
                self.w_taskPreset = QWidget()
                self.lo_taskPreset = QHBoxLayout(self.w_taskPreset)
                self.lo_taskPreset.setContentsMargins(0, 0, 0, 0)
                self.chb_taskPreset = QCheckBox("Task Preset")
                self.cb_taskPreset = QComboBox()
                self.lo_taskPreset.addWidget(self.chb_taskPreset)
                self.lo_taskPreset.addWidget(self.cb_taskPreset)
                self.lo_taskPreset.addStretch()
                self.cb_taskPreset.setEnabled(self.chb_taskPreset.isChecked())
                self.chb_taskPreset.toggled.connect(self.cb_taskPreset.setEnabled)
                self.chb_taskPreset.toggled.connect(lambda state: self.tw_steps.setEnabled(not state))
                self.chb_taskPreset.toggled.connect(lambda state: self.chb_category.setEnabled(not state))
                self.chb_taskPreset.toggled.connect(lambda state: self.enableOk())
                if self.entities[0]["type"] in ["asset"]:
                    presets = self.core.projects.getAssetTaskPresets()
                else:
                    presets = self.core.projects.getShotTaskPresets()

                if presets:
                    for preset in presets:
                        self.cb_taskPreset.addItem(preset.get("name", ""), preset)

                    self.verticalLayout.insertWidget(2, self.w_taskPreset)

        if self.mode == "tasks":
            self.e_tasks = QLineEdit()
            allowAdditionalTasks = self.core.getConfig("globals", "allowAdditionalTasks", config="project", dft=True)
            if allowAdditionalTasks:
                self.w_tasks = QWidget()
                self.lo_tasks = QHBoxLayout()
                self.lo_tasks.setContentsMargins(0, 0, 0, 0)
                self.w_tasks.setLayout(self.lo_tasks)
                self.l_tasks = QLabel("Additional Tasks:")
                self.e_tasks.textEdited.connect(lambda x: self.enableOk())
                self.e_tasks.setPlaceholderText("Separate tasks using \",\"")
                self.lo_tasks.addWidget(self.l_tasks)
                self.lo_tasks.addWidget(self.e_tasks)

                self.verticalLayout.insertWidget(1, self.w_tasks)

        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.tw_steps.itemSelectionChanged.connect(self.selectionChanged)
        self.tw_steps.customContextMenuRequested.connect(self.rclList)

    @err_catcher(name=__name__)
    def rclList(self, pos):
        if self.entities:
            rcmenu = QMenu(self)

            if self.mode == "departments":
                exp = QAction("Create new department...", self)
                exp.triggered.connect(self.createDepartment)
                rcmenu.addAction(exp)

                exp = QAction("Manage project departments...", self)
                exp.triggered.connect(self.manageDepartments)
                rcmenu.addAction(exp)
            elif self.mode == "tasks":
                exp = QAction("Manage project tasks...", self)
                exp.triggered.connect(self.manageTasks)
                rcmenu.addAction(exp)

            rcmenu.exec_(QCursor.pos())

    @err_catcher(name=__name__)
    def selectionChanged(self):
        self.enableOk()
        if self.mode == "departments":
            items = self.tw_steps.selectedItems()
            if len(items) == 0:
                txt = "Create default tasks"
            elif len(items) == 1:
                abbr = items[0].data(Qt.UserRole)["abbreviation"]
                defaultTasks = self.core.entities.getDefaultTasksForDepartment(self.entities[0]["type"], abbr)
                if defaultTasks:
                    txt = "Create default tasks: \"%s\"" % "\", \"".join(defaultTasks)
                else:
                    txt = "Create default tasks"
            else:
                txt = "Create default tasks for each department"

            self.chb_category.setText(txt)

    @err_catcher(name=__name__)
    def enableOk(self):
        enabled = len(self.tw_steps.selectedItems()) > 0
        if self.mode == "tasks" and self.e_tasks.text():
            enabled = True
        elif self.getTaskPreset():
            enabled = True

        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(enabled)
        if self.core.appPlugin.pluginName != "Standalone" or self.mode != "tasks":
            if self.mode == "departments":
                nextEnabled = len([x for x in self.tw_steps.selectedItems() if x.column() == 0]) == 1 and not self.getTaskPreset()
                self.b_next.setEnabled(nextEnabled)
            elif self.mode == "tasks":
                self.b_next.setEnabled(bool(enabled or self.e_tasks.text()))

    @err_catcher(name=__name__)
    def getTaskPreset(self):
        if not self.entities:
            return

        if self.mode != "departments":
            return

        if not self.chb_taskPreset.isChecked():
            return

        return self.cb_taskPreset.currentData()

    @err_catcher(name=__name__)
    def createDepartment(self):
        self.dlg_department = PrismWidgets.CreateDepartmentDlg(core=self.core, entity=self.entities[0]["type"], parent=self)
        self.dlg_department.departmentCreated.connect(self.onDepartmentCreated)
        self.dlg_department.exec_()

    @err_catcher(name=__name__)
    def manageDepartments(self):
        self.close()
        self.core.prismSettings(tab="Departments", settingsType="Project")

    @err_catcher(name=__name__)
    def manageTasks(self):
        self.close()
        dlg = self.core.prismSettings(tab="Departments", settingsType="Project")
        entities = self.core.pb.sceneBrowser.getCurrentEntities()
        dep = self.core.pb.sceneBrowser.getCurrentDepartment()
        if entities[0].get("type") == "asset":
            for idx in range(dlg.w_project.tw_assetDepartments.rowCount()):
                itemDep = dlg.w_project.tw_assetDepartments.item(idx, 0).data(Qt.UserRole).get("abbreviation")
                if itemDep == dep:
                    row = idx
                    break
            else:
                return

            dlg.w_project.tw_assetDepartments.selectRow(row)
        elif entities[0].get("type") in ["shot", "sequence"]:
            for idx in range(dlg.w_project.tw_shotDepartments.rowCount()):
                itemDep = dlg.w_project.tw_shotDepartments.item(idx, 0).data(Qt.UserRole).get("abbreviation")
                if itemDep == dep:
                    row = idx
                    break
            else:
                return

            dlg.w_project.tw_shotDepartments.selectRow(row)

    @err_catcher(name=__name__)
    def onDepartmentCreated(self, department):
        rc = self.tw_steps.rowCount()
        self.tw_steps.insertRow(rc)
        name = "%s (%s)" % (department["name"], department["abbreviation"])
        nameItem = QTableWidgetItem(name)
        nameItem.setData(Qt.UserRole, department)
        self.tw_steps.setItem(rc, 0, nameItem)
        self.tw_steps.selectRow(rc)

    @err_catcher(name=__name__)
    def buttonboxClicked(self, button):
        if button.text() == "Create":
            if self.mode == "passes":
                pass
            elif self.mode == "departments":
                preset = self.getTaskPreset()
                if preset:
                    createdDirs = False
                    for entity in self.entities:
                        result = self.core.entities.createTasksFromPreset(entity, preset)
                        if result:
                            createdDirs = True

                    if createdDirs:
                        self.core.pb.sceneBrowser.refreshDepartments()

                else:
                    steps = []
                    for i in self.tw_steps.selectedItems():
                        if i.column() == 0:
                            steps.append(i.data(Qt.UserRole)["abbreviation"])

                    self.core.pb.sceneBrowser.createSteps(self.entities, steps, createTask=self.chb_category.isChecked())

            elif self.mode == "tasks":
                tasks = []
                for item in self.tw_steps.selectedItems():
                    if item.column() == 0:
                        tasks.append(item.data(Qt.UserRole))

                tasks += [t.strip() for t in self.e_tasks.text().split(",") if t]                
                self.core.pb.sceneBrowser.createTask(tasks)

            self.accept()
        elif button.text() == self.btext:
            if self.entities:
                self.stepBbClicked(button)
                self.accept()

        elif button.text() == "Cancel":
            self.reject()

    @err_catcher(name=__name__)
    def stepBbClicked(self, button):
        if button.text() == self.btext:
            if self.mode == "departments":
                for i in self.tw_steps.selectedItems():
                    if i.column() == 0:
                        step = i.data(Qt.UserRole)["abbreviation"]

                self.core.pb.sceneBrowser.createSteps(self.entities, [step], createTask=False)
                self.close()
                self.core.pb.sceneBrowser.createTaskDlg()
            elif self.mode == "tasks":
                tasks = []
                for item in self.tw_steps.selectedItems():
                    if item.column() == 0:
                        tasks.append(item.data(Qt.UserRole))

                tasks += [t.strip() for t in self.e_tasks.text().split(",") if t]                
                self.core.pb.sceneBrowser.createTask(tasks)
                self.reject()
                if self.core.appPlugin.pluginName != "Standalone":
                    self.core.pb.sceneBrowser.createFromCurrent()
                    self.core.pb.close()

    @err_catcher(name=__name__)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.tw_steps.selectedItems():
                if self.entities:
                    if self.core.appPlugin.pluginName != "Standalone":
                        self.stepBbClicked(self.b_next)
                    else:
                        self.stepBbClicked(self.buttonBox.buttons()[0])
                else:
                    self.accept()
        elif event.key() == Qt.Key_Escape:
            self.reject()
