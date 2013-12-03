#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2013, Cameron White
from .. import TOKEN_PATH
from .tools import waiting_effects
from ..tools import load_token, store_token, generate_tokens
from github import Github
from github.GithubException import GithubException
from github.Authorization import Authorization
from PyQt4.QtCore import QRegExp, QRect, Qt, QPoint
from PyQt4.QtGui import QWizardPage, QWizard, QRadioButton, QLineEdit, \
    QRegExpValidator, QVBoxLayout, QHBoxLayout, QLabel, QMainWindow, \
    QDialog, QIcon, QAction, QSizePolicy, QPushButton, QWidget, \
    QTableWidget, QTableWidgetItem, QAbstractItemView, QPixmap, \
    QFormLayout, QDialogButtonBox, QValidator, QMenu
from AddRepoWizard import AddRepoWizard
from AddAccountWizard import AddAccountWizard
import urllib

class MainWidget(QMainWindow):

    def __init__(self, parent=None):
        super(MainWidget, self).__init__(
                parent,
                windowTitle='GitRemote',
                windowIcon=QIcon('images/git.png'),
                geometry=QRect(300, 300, 600, 372))

        self.github = None        

        # Actions

        self.repoAddAction = QAction(
                QIcon('images/plus_48.png'),
                '&Add Repo', self,
                statusTip='Add a new repo')
        self.repoAddAction.triggered.connect(self.repoAdd)
        
        self.repoRemoveAction = QAction(
                QIcon('images/minus.png'),
                '&Remove Repo', self,
                statusTip='Remove repo')
        self.repoRemoveAction.triggered.connect(self.repoRemove)

        self.repoRefreshAction = QAction(
                QIcon('images/refresh.png'),
                'Refresh Repos', self,
                statusTip='Refresh list of repos')
        self.repoRefreshAction.triggered.connect(self.reposRefresh)

        self.addAccountAction = QAction(
                'Add Account', self,
                statusTip='Add Account')
        self.addAccountAction.triggered.connect(self.addAccount)

        # userPushButton - Displays the current active username and 
        # image on the top right of the toolbar. TODO Attach a menu
        # of all logged in users.

        self.userMenu = QMenu('user accounts menu')

        self.userLabel = QLabel(self)
        self.userLabel.setScaledContents(True)
        self.userLabel.setSizePolicy(
                QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored))

        self.userImageLabel = QLabel(self)
        self.userImageLabel.setScaledContents(True)
        self.userLabel.setSizePolicy(
                QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))

        self.userPushButton = QPushButton(self)
        self.userPushButton.setSizePolicy(
                QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum))

        hbox = QHBoxLayout()
        hbox.addWidget(self.userImageLabel)
        hbox.addWidget(self.userLabel)
        self.userPushButton.setLayout(hbox)
        self.userPushButton.setMenu(self.userMenu)

        # ToolBar

        self.toolBar = self.addToolBar('Main')
        self.toolBar.setMovable(False)
        self.toolBar.setFloatable(False)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolBar.addAction(self.repoAddAction)
        self.toolBar.addAction(self.repoRemoveAction)
        self.toolBar.addAction(self.repoRefreshAction)
        self.toolBar.addWidget(spacer)
        self.toolBar.addWidget(self.userPushButton)

        # Menu

        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        actionMenu = menuBar.addMenu('&Action')
        fileMenu.addAction(self.addAccountAction)
        actionMenu.addAction(self.repoAddAction)
        actionMenu.addAction(self.repoRemoveAction)
        actionMenu.addAction(self.repoRefreshAction)

        # StatusBar

        statusBar = self.statusBar()
        self.setStatusBar(statusBar)

        # reposTableWidget - Displays a list of the users repositories

        self.reposTableWidgetHeaders = ["Icon", "Name"]
        self.reposTableWidget = QTableWidget(0,
                len(self.reposTableWidgetHeaders),
                selectionBehavior = QAbstractItemView.SelectRows,
                selectionMode = QAbstractItemView.SingleSelection,
                editTriggers = QAbstractItemView.NoEditTriggers,
                itemSelectionChanged = self.actionsUpdate)
        self.reposTableWidget.setHorizontalHeaderLabels(
                self.reposTableWidgetHeaders)
        self.reposTableWidget.horizontalHeader().setStretchLastSection(True)
        self.reposTableWidget.horizontalHeader().setVisible(False)
        self.reposTableWidget.verticalHeader().setVisible(False)
        self.reposTableWidget.setShowGrid(False)

        # Layout

        self.setCentralWidget(self.reposTableWidget)
        self.actionsUpdate()
        self.show()
        
        # Update

        self.loadUserMenu()
        self.activeUserAction.setVisible(False)
        self.authenticate()
        self.actionsUpdate()
        self.reposRefresh()
        self.updateImage()
    
    @waiting_effects
    def updateImage(self):

        try:
            url = self.github.get_user().avatar_url
        except (GithubException, AttributeError): 
            return 
        data = urllib.urlopen(url).read()
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.activeUserAction.setIcon(QIcon(pixmap))
        self.userImageLabel.setPixmap(pixmap)
        self.userImageLabel.setFixedSize(32, 32)
        self.userLabel.setText(self.github.get_user().login)
        size = self.userLabel.sizeHint()
        # TODO - Remove magic numbers
        self.userPushButton.setFixedSize(size.width() + 70, 48)
        self.userMenu.setFixedWidth(size.width() + 70)
   
    @waiting_effects
    def loadUserMenu(self):
        
        action = None
        for _, username, token in generate_tokens(TOKEN_PATH, 'github'):
            
            try:
                url = Github(token).get_user().avatar_url
            except (GithubException, AttributeError): 
                action = QAction(username, self, triggered=self.changeActive)
                self.userMenu.addAction(action)
                continue
            data = urllib.urlopen(url).read()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            pixmap.scaled(32,32)
            action = QAction(QIcon(pixmap), username, self,
                    triggered=self.changeActive)
            action.setIconVisibleInMenu(True)
            self.userMenu.addAction(action)
        
        self.activeUserAction = action
    
    def changeActive(self):

        sender = self.sender()

        self.activeUserAction.setVisible(True)
        self.activeUserAction = sender
        self.activeUserAction.setVisible(False)
        self.authenticate()
        self.actionsUpdate()
        self.reposRefresh()
        self.updateImage()

    @waiting_effects
    def reposRefresh(self):
        repo_pixmap = QPixmap('images/book_32.png')
        fork_pixmap = QPixmap('images/book_fork_32.png')
        try:
            repos = self.github.get_user().get_repos()
            self.reposTableWidget.setRowCount(self.github.get_user().public_repos)
        except (GithubException, AttributeError):
            return
        for row, repo in enumerate(repos):
            imageLabel = QLabel()
            if repo.fork:
                imageLabel.setPixmap(fork_pixmap)
            else:
                imageLabel.setPixmap(repo_pixmap)
            imageLabel.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            imageLabel.setFixedWidth(imageLabel.sizeHint().width() + 10)
            self.reposTableWidget.setCellWidget(row, 0, imageLabel)
            label = QLabel(
                    '<pre><b>{}</b>\n{}</pre>'.format(
                        str(repo.name), str(repo.description)))
            label.setAlignment(Qt.AlignVCenter)
            labelHeight = max(label.sizeHint().height(),
                    imageLabel.sizeHint().height())
            label.setFixedHeight(labelHeight + 10)
            self.reposTableWidget.setCellWidget(row, 1, label)
        for i in range(self.reposTableWidget.columnCount()-1):
            self.reposTableWidget.resizeColumnToContents(i)
        self.reposTableWidget.resizeRowsToContents()

    @waiting_effects
    def authenticate(self):
        
        username = str(self.activeUserAction.text())
        try:
            token = load_token(TOKEN_PATH, 'github', username) 
            self.github = Github(token)
        except IOError, EOFError:
            self.github = None
    
    def actionsUpdate(self):
        # TODO disable if no user is logged in
        if self.github is None:
            self.repoAddAction.setEnabled(False)
            self.repoRemoveAction.setEnabled(False)
            self.repoRefreshAction.setEnabled(False)
        else:
            self.repoAddAction.setEnabled(True)
            self.repoRefreshAction.setEnabled(True)
            if self._isARepoSelected():
                self.repoRemoveAction.setEnabled(True)
            else:
                self.repoRemoveAction.setEnabled(False)

    def addAccount(self):
        wizard = AddAccountWizard(self)
        if wizard.exec_():
            username = str(wizard.field('username').toString())
            token = str(wizard.field('token').toString())
            store_token(TOKEN_PATH, 'github', username, token)
            self.authenticate()
            self.reposRefresh()
            self.updateImage()
            self.actionsUpdate()
    

    def repoAdd(self):
        wizard = AddRepoWizard(self.github, self)
        if wizard.exec_():
            self.github.get_user().create_repo(
                str(wizard.field('name').toString()),
                description=str(wizard.field('description').toString()),
                private=bool(wizard.field('private').toBool()),
                auto_init=bool(wizard.field('auto_init').toBool()),
                gitignore_template=str(wizard.field('gitignore').toString()),
                homepage=str(wizard.field('homepage').toString()),
                has_wiki=bool(wizard.field('has_wiki').toBool()),
                has_downloads=bool(wizard.field('has_downloads').toBool()),
                has_issues=bool(wizard.field('has_issues').toBool()))
            self.reposRefresh()
    
    def repoRemove(self):
        
        row = self._selectedRepoRow()
        name = self.reposTableWidget.item(row, 0).text()
        dialog = RepoRemoveDialog(self.github, name)
        if dialog.exec_():
            self.github.get_user().get_repo(str(name)).delete()
            self.reposRefresh()

    def _isARepoSelected(self):
        """ Return True if a repo is selected else False """
        if len(self.reposTableWidget.selectedItems()) > 0:
            return True
        else:
            return False

    def _selectedRepoRow(self):
        """ Return the currently select repo """
        # TODO - figure out what happens if no repo is selected
        selectedModelIndexes = \
            self.reposTableWidget.selectionModel().selectedRows()
        for index in selectedModelIndexes:
            return index.row()

class RepoRemoveDialog(QDialog):
    def __init__(self, github, name, parent=None):
        super(RepoRemoveDialog, self).__init__(
            parent,
            windowTitle="Remove Repo")

        self.github = github 
        self.login = self.github.get_user().login
        self.name = name

        self.label = QLabel('''
        <p>Are you sure?</p>

        <p>This action <b>CANNOT</b> be undone.</p>
        <p>This will delete the <b>{}/{}</b> repository, wiki, issues, and
        comments permanently.</p>

        <p>Please type in the name of the repository to confirm.</p>
        '''.format(self.login, self.name))
        self.label.setTextFormat(Qt.RichText)
       
        validator = QRegExpValidator(
                QRegExp(r'{}/{}'.format(self.login, self.name)))
        self.nameEdit = QLineEdit(textChanged=self.textChanged)
        self.nameEdit.setValidator(validator)

        # Form

        self.form = QFormLayout()
        self.form.addRow(self.label)
        self.form.addRow(self.nameEdit)
        
        # ButtonBox

        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            accepted=self.accept, rejected=self.reject)
        
        # Layout

        self.mainLayout = QVBoxLayout()
        self.mainLayout.addLayout(self.form)
        self.mainLayout.addWidget(self.buttonBox)
        self.setLayout(self.mainLayout)
        
        self.textChanged()

    def textChanged(self):
        
        if self.nameEdit.validator().validate(self.nameEdit.text(), 0)[0] \
                == QValidator.Acceptable:
            b = True
        else:
            b = False
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(b)
