# This Python file uses the following encoding: utf-8


import gvsig
from gvsig import getResource
from gvsig import commonsdialog
from gvsig.uselib import use_plugin
from gvsig.libs.formpanel import FormPanel, FormComponent, ActionListenerAdapter

import os.path
import datetime

from java.lang import Throwable

from java.nio.charset import Charset

from java.awt import BorderLayout
from javax.swing import Timer
from javax.swing import ButtonGroup
from javax.swing import JMenuItem
from javax.swing import JCheckBoxMenuItem
from javax.swing import JPopupMenu

from org.gvsig.tools import ToolsLocator
from org.gvsig.tools.swing.api import ToolsSwingLocator
from org.gvsig.andami import PluginsLocator
from org.gvsig.app import ApplicationLocator
from org.gvsig.app.gui.panels import CRSSelectPanelFactory
from org.gvsig.fmap.dal.swing.dataStoreParameters import AbstractDataStoreParametersPanelFactory
from org.gvsig.fmap.dal.swing.dataStoreParameters import AbstractDataStoreParametersPanel
from org.gvsig.fmap.dal import DALLocator
from org.gvsig.fmap.geom import DataTypes
from org.gvsig.fmap.dal.swing import DALSwingLocator
from org.gvsig.tools.swing.api.windowmanager import WindowManager

from addons.CSVWizard.parametersio import ParametersIO

#from parametersio import ParametersIO

class CSVWizardFactory(AbstractDataStoreParametersPanelFactory):
    def create(self, parameters):
      """
      Create the properties panel associated to the parameters.
      @param parameters
      @return the properties panel.
      """
      wizard = CSVWizard()
      wizard.putParameters(parameters)
      return wizard
      
    def canBeApplied(self, parameters):
      """
      Return true if this factory can apply to the parameters.
       
      @param parameters
      @return true if this factory can apply to the parameters
      """
      return parameters.__class__.__name__ == "CSVStoreParameters"
            
    def getPriority(self):
      """
      The priority of this factory.
      Cuando hay mas de una factoria aplicable a unos parametros es cogida la
      de prioridad mas alta.
       
      @return the priority of this factory
      """
      return 1000   

    def selfRegister(self):
      DALSwingLocator.getDataStoreParametersPanelManager().registerFactory(self)
      
class LocaleItem(object):
  def __init__(self, locale, localeLabel):
    self.locale = locale
    self.localeLabel = localeLabel

  def __str__(self):
    return self.localeLabel

  toString = __str__
  __repr__ = __str__
  
  def getLocale(self):
    return self.locale
    
class ColumnType(object):

  def __init__(self, name=None, typeName=None, calculated=False):
    self.name = name
    self.typeName = typeName
    self.pos1 = 0
    self.pos2 = -1
    self.calculated = calculated

  def __str__(self):
    return "%s,%s,%s.%s,%s" % (self.name,self.typeName,self.pos1,self.pos2,self.calculated)
    
class ColumnTypes(FormComponent):  # pylint: disable=R0904

  def __init__(self, lblColumn, cboColumn,
    lblColumnName, txtColumnName,
    lblColumnType, cboColumnType,
    lblColumnPosition, txtColumnPositionFirst, txtColumnPositionLast):

    FormComponent.__init__(self)

    self.lblColumn = lblColumn
    self.cboColumn = cboColumn
    self.lblColumnName = lblColumnName
    self.txtColumnName = txtColumnName
    self.lblColumnType = lblColumnType
    self.cboColumnType = cboColumnType
    self.lblColumnPosition = lblColumnPosition
    self.txtColumnPositionFirst = txtColumnPositionFirst
    self.txtColumnPositionLast = txtColumnPositionLast

    self.discardFireChanges = False
    self.changeListeners = list()
    self.columnTypes = None
    self.current = -1

    dataTypesManager = ToolsLocator.getDataTypesManager()
    self.geometryTypeName = dataTypesManager.get(DataTypes.GEOMETRY).getName()

    self.autobind()
    self.fillComboDataTypes()
    self.setFixedSize(False)
    self.clear()

  def fillComboDataTypes(self):
    items = list()
    dataTypesManager = ToolsLocator.getDataTypesManager()
    for dataType in dataTypesManager.iterator():
      #if dataType.isObject() or dataType.isDynObject() or dataType.isContainer():
      if dataType.isDynObject() or dataType.isContainer():
        continue
      items.append(dataType.getName())
    items.sort()
    for item in items:
      self.cboColumnType.addItem(item)

  def setFixedSize(self,fixedSize):
    #print "ColumnTypes.setFixedSize(%s)" % fixedSize
    self.fixedSize = fixedSize

  def isFixedSize(self):
    return self.fixedSize
    
  def setEnabled(self,enabled):
    #print "ColumnTypes.setEnabled(%s)" % enabled
    self.cboColumn.setEnabled(enabled)

    if self.columnTypes!=None and self.current>=0:
      columnType = self.columnTypes[self.current]
      enabled = not columnType.calculated
      
    self.txtColumnName.setEnabled(enabled)
    self.cboColumnType.setEnabled(enabled)
    
    if enabled :
      enabled = self.fixedSize
    self.lblColumnPosition.setEnabled(enabled)
    self.txtColumnPositionFirst.setEnabled(enabled)
    self.txtColumnPositionLast.setEnabled(enabled)

  def enableComponents(self):
    #print "ColumnTypes.enableComponents(): %s" % (self.columnTypes != None)
    self.setEnabled(self.columnTypes != None)
    
  def clear(self):
    #print "ColumnTypes.clear()"
    self.columnTypes = None
    self.current = -1
    self.txtColumnName.setText("")
    self.cboColumnType.setSelectedIndex(-1)
    self.cboColumn.setSelectedIndex(-1)
    self.txtColumnPositionFirst.setText("")
    self.txtColumnPositionLast.setText("")
    self.setEnabled(False)
    
  def setStore(self, store):
    #print "ColumnTypes.setStore"
    if store == None:
      self.clear()
      return
    self.columnTypes = list()
    ft = store.getDefaultFeatureType()
    for at in ft.getAttributeDescriptors():
      calculated = (at.getEvaluator()!=None or at.getFeatureAttributeEmulator()!=None)
      self.columnTypes.append(ColumnType(at.getName(), at.getDataTypeName(),calculated))
    self.cboColumn.removeAllItems()
    for n in range(0,len(self.columnTypes)):
      self.cboColumn.addItem(n)
    storeParameters = store.getParameters()
    self.setFixedFielDefinition(storeParameters.getDynValue("fieldsDefinition"))
    self.setCurrent(0)
    self.enableComponents()

  def setCurrent(self, current):
    #print "ColumnTypes.setCurrent(%s)" % current
    if self.columnTypes == None or current <0 or current >=len(self.columnTypes):
      return
    discardFireChanges = self.discardFireChanges
    self.discardFireChanges = True
    self.current = current
    columnType = self.columnTypes[self.current]
    if self.cboColumn.getSelectedIndex()!= self.current :
      self.cboColumn.setSelectedIndex(self.current)
    self.txtColumnName.setText(columnType.name)
    self.cboColumnType.setSelectedItem(columnType.typeName)
    self.txtColumnPositionFirst.setText(str(columnType.pos1))
    self.txtColumnPositionLast.setText(str(columnType.pos2))
    self.enableComponents()
    self.discardFireChanges = discardFireChanges

  def setTypeName(self, typeName):
    #print "ColumnTypes.setTypeName(%r)" % typeName
    if self.columnTypes == None or self.current <0 :
      return
    self.columnTypes[self.current].typeName = typeName

  def getTypeName(self):
    if self.columnTypes == None or self.current <0 :
      return None
    return self.columnTypes[self.current].typeName
    
  def getName(self):
    if self.columnTypes == None or self.current <0 :
      return None
    return self.columnTypes[self.current].name
    
  def setName(self, name):
    #print "ColumnTypes.setName(%r)" % name
    if self.columnTypes == None or self.current <0 :
      return
    self.columnTypes[self.current].name = name

  def setPos1(self, pos):
    if self.columnTypes == None or self.current <0 :
      return
    self.columnTypes[self.current].pos1 = pos

  def getPos1(self):
    if self.columnTypes == None or self.current <0 :
      return None
    return self.columnTypes[self.current].pos1

  def setPos2(self, pos):
    if self.columnTypes == None or self.current <0 :
      return
    self.columnTypes[self.current].pos2 = pos

  def getPos2(self):
    if self.columnTypes == None or self.current <0 :
      return None
    return self.columnTypes[self.current].pos2

  def setColumnsCount(self,columnsCount):
    if not self.fixedSize or columnsCount<1:
      return
    if self.columnTypes == None:
      self.columnTypes = list()
    if len(self.columnTypes)<columnsCount :
      for n in range(len(self.columnTypes),columnsCount):
        self.columnTypes.append(ColumnType(self.getColumnName(n), "String",False))
    else:
      while len(self.columnTypes)>columnsCount:
        del self.columnTypes[-1]
    self.setCurrent(0)
    self.enableComponents()

  def getColumnName(self, n):
    return chr(65+(n/100)%10)+chr(65+(n/10)%10)+chr(65+n % 10)
    
  def getHeader(self, delimiter=","):
    if self.columnTypes == None:
      return None
    header = ""
    for columnType in self.columnTypes:
      if not columnType.calculated:
        header += columnType.name + "__" + columnType.typeName + delimiter
    #print "ColumnTypes.getHeader(%r): %r" % (delimiter,header)
    return header   

  def setHeader(self, headers, delimiter):
    if headers == None:
      return
    if delimiter == None:
      delimiter = ";"
    self.columnTypes = list()
    headers2 = headers.split(delimiter)
    for header in headers2:
      if header.strip()=="":
        continue
      ss = header.split("__")
      self.columnTypes.append(ColumnType(ss[0], ss[1],False))
    self.setCurrent(0)
    self.enableComponents()

  def getFixedFielDefinition(self):
    definition = ""
    for columnType in self.columnTypes:
      definition += "%s:%s " % (columnType.pos1,columnType.pos2)
    return definition

  def setFixedFielDefinition(self, definitions):
    if definitions == None:
      return
    if self.columnTypes == None:
      self.columnTypes = list()
    n = 0
    ss1 = definitions.split(" ")
    for s1 in ss1:
      if n<len(self.columnTypes):
        columnType = self.columnTypes[n]
        ss2 = s1.split(":")
        try:
          columnType.pos1 = int(ss2[0])
        except:
          pass
        try:
          columnType.pos2 = int(ss2[1])
        except:
          pass
        if columnType.name in (None, ""):
          columnType.name = self.getColumnName(n)
        if columnType.typeName in (None, ""):
          columnType.typeName = "String"
        n+=1
    self.setCurrent(0)
    self.enableComponents()
      
  def addChangeListener(self, func):
    self.changeListeners.append(func)

  def fireChange(self):
    if self.discardFireChanges:
      return
    for listener in self.changeListeners:
      try:
        listener()
      except:
        pass
        
  def cboColumn_change(self, *args):
    self.setCurrent(self.cboColumn.getSelectedIndex())
  
  def txtColumnName_change(self, *args):
    if self.getName()!=self.txtColumnName.getText():
      self.setName(self.txtColumnName.getText())
      self.fireChange()
    else:
      self.setName(self.txtColumnName.getText())

  def cboColumnType_change(self, *args):
    if self.getTypeName()!=self.cboColumnType.getSelectedItem():
      self.setTypeName(self.cboColumnType.getSelectedItem())
      self.fireChange()
    else:
      self.setTypeName(self.cboColumnType.getSelectedItem())

  def txtColumnPositionFirst_change(self, *args):
    s = self.txtColumnPositionFirst.getText()
    if s in (None, ""):
      return
    old = self.getPos1()
    try:
      self.setPos1(int(s))
    except:
      return
    if old != self.getPos1():
      self.fireChange()
    
  def txtColumnPositionLast_change(self, *args):
    s = self.txtColumnPositionLast.getText()
    if s in (None, ""):
      return
    old = self.getPos2()
    try:
      self.setPos2(int(s))
    except:
      return
    if old != self.getPos2():
      self.fireChange()

  def txtColumnPositionFirst_focusGained(self,*args):
    self.txtColumnPositionFirst.selectAll()
    
  def txtColumnPositionLast_focusGained(self,*args):
    self.txtColumnPositionLast.selectAll()
    
  def txtColumnName_focusGained(self,*args):
    self.txtColumnName.selectAll()
    

class CSVWizard(FormPanel, AbstractDataStoreParametersPanel): # pylint: disable=R0904

  def __init__(self):
    FormPanel.__init__(self)
    self._parameters = None
    self.file = None
    self.providerName = None
    self.featureTable = None
    self.currentStore = None
    self._autorefresh = False
    self.crs = None
    self.columnTypes = None
    self.initComponents()

  def initComponents(self):
    self.timerAutorefresh = Timer(2000,None)
    self.mnuSaveParameters = JMenuItem("Save parameters...")
    self.mnuLoadParameters = JMenuItem("Load parameters...")
    self.mnuAutomaticPreview = JCheckBoxMenuItem("Automatic preview")
    self.mnuOptions = JPopupMenu()
    self.mnuOptions.add(self.mnuSaveParameters)
    self.mnuOptions.add(self.mnuLoadParameters)
    self.mnuOptions.add(self.mnuAutomaticPreview)
    
    self.load(getResource(__file__,"CSVWizard.xml"))
        
    self.columnTypes = ColumnTypes(
      self.lblColumn, self.cboColumn,
      self.lblColumnName, self.txtColumnName,
      self.lblColumnType, self.cboColumnType,
      self.lblColumnPosition, self.txtColumnPositionFirst, self.txtColumnPositionLast
    )
    self.columnTypes.addChangeListener(self.columnTypes_change)
    self.fillComboCharSet()
    self.fillComboLocale()
    self.btgUsarSeparadores = ButtonGroup()
    self.btgUsarSeparadores.add(self.rdbFixedSize)
    self.btgUsarSeparadores.add(self.rdbUseSeparator)
    self.btgSeparador = ButtonGroup()
    self.btgSeparador.add(self.rdbUseTab)
    self.btgSeparador.add(self.rdbUseColon)
    self.btgSeparador.add(self.rdbUseSemiColon)
    self.btgSeparador.add(self.rdbUseSpace)
    self.btgSeparador.add(self.rdbUseOther)
    self.btgGeometria = ButtonGroup()
    self.btgGeometria.add(self.rdbWithoutGeometry)
    self.btgGeometria.add(self.rdbColumnsXYZ)
    self.btgGeometria.add(self.rdbWKTGeometry)
    self.btnPreview.setVisible(True)

    self.translateUI()    

    # El campo txtColumnName sale muy pequeño, le damos 80px mas de ancho
    size = self.getPreferredSize()
    self.setPreferredSize(size.width+80,size.height)
    
    
    self.enableComponents()
    
    self.mnuAutomaticPreview.setSelected(False)

  def translateUI(self):
    i18nManager = ToolsLocator.getI18nManager()

    self.lblCharSet.setText(i18nManager.getTranslation("_Character_set"))
    self.lblLocale.setText(i18nManager.getTranslation("_Regional_configuration"))
    self.lblUseHeader.setText(i18nManager.getTranslation("_First_row_as_header"))
    self.lblSkipFromLine.setText(i18nManager.getTranslation("_From_row"))
    self.lblCommentStartMarker.setText(i18nManager.getTranslation("_Comment_start_marker"))
    self.lblIgnoreErrors.setText(i18nManager.getTranslation("_Ignore_errors"))
    self.rdbUseSeparator.setText(i18nManager.getTranslation("_Use_separator"))
    self.rdbUseTab.setText(i18nManager.getTranslation("_Tab_key"))
    self.rdbUseColon.setText(i18nManager.getTranslation("_Comma"))
    self.rdbUseSemiColon.setText(i18nManager.getTranslation("_Semicolon"))
    self.rdbUseSpace.setText(i18nManager.getTranslation("_Space"))
    self.rdbUseOther.setText(i18nManager.getTranslation("_Other"))
    self.lblQuoteCharacter.setText(i18nManager.getTranslation("_Text_delimiter"))
    self.lblEscapeCharacter.setText(i18nManager.getTranslation("_Escape_character"))
    self.rdbFixedSize.setText(i18nManager.getTranslation("_Use_fixed_width"))
    self.lblColumnsCount.setText(i18nManager.getTranslation("_Columns"))
    self.lblColumn.setText(i18nManager.getTranslation("_Column"))
    self.lblColumnName.setText(i18nManager.getTranslation("_Name"))
    self.lblColumnType.setText(i18nManager.getTranslation("_Type"))
    self.lblColumnPosition.setText(i18nManager.getTranslation("_Position"))
    self.btnOptions.setText(i18nManager.getTranslation("_Options"))
    self.btnPreview.setText(i18nManager.getTranslation("_Preview"))
    self.rdbWithoutGeometry.setText(i18nManager.getTranslation("_Without_geometric_information"))
    self.rdbColumnsXYZ.setText(i18nManager.getTranslation("_Columns_with_values_for_X_Y_Z"))
    self.lblGeomName.setText(i18nManager.getTranslation("_Name"))
    self.lblColumnX.setText(i18nManager.getTranslation("_X"))
    self.lblColumnY.setText(i18nManager.getTranslation("_Y"))
    self.lblColumnZ.setText(i18nManager.getTranslation("_Z"))
    self.lblCRS.setText(i18nManager.getTranslation("_CRS"))
    self.sptSeparatorOptions.setText(i18nManager.getTranslation("_Options_separator"))
    self.sptColumns.setText(i18nManager.getTranslation("_Columns"))    
    self.mnuSaveParameters.setText(i18nManager.getTranslation("_Save_parameters_XellipsisX"))
    self.mnuLoadParameters.setText(i18nManager.getTranslation("_Load_parameters_XellipsisX"))
    self.mnuAutomaticPreview.setText(i18nManager.getTranslation("_Automatic_preview"))
        
    self.tabOptions.setTitleAt(0,i18nManager.getTranslation("_General"))
    self.tabOptions.setTitleAt(1,i18nManager.getTranslation("_Geometry"))
    
  def fillComboCharSet(self):
    availableCharsets = Charset.availableCharsets().keySet()
    for charset in availableCharsets:
      self.cboCharSet.addItem(charset)
    self.cboCharSet.setSelectedItem("UTF-8")
    
  def fillComboLocale(self):
    localeManager = PluginsLocator.getLocaleManager()
    availableLocales = localeManager.getInstalledLocales()
    items = list()
    for locale in availableLocales:
      items.append(LocaleItem(locale,localeManager.getLocaleDisplayName(locale)))
    n = 0
    selected = -1
    items.sort()
    for item in items:
      if item.getLocale() == localeManager.getCurrentLocale():
        selected = n
      self.cboLocale.addItem(item)
      n += 1
    self.cboLocale.setSelectedIndex(selected)

  def setLocale(self, locale):
    if locale in ("", None):
      localeManager = PluginsLocator.getLocaleManager()
      locale = localeManager.getCurrentLocale().toString()
    model = self.cboLocale.getModel()
    for n in range(model.getSize()):
      item =  model.getElementAt(n)
      if item.getLocale().toString() == locale:
        model.setSelectedItem(item)
        return
        
  def setAutorefresh(self, autorefresh):
    #print "setAutorefresh:", autorefresh
    self._autorefresh = autorefresh

  def setExcludeGeometryOptions(self, excludeGeometryOptions):
    """
    Fija si se tienen que mostrar las opciones relacionadas con campos
    de tipo geometria o no.
    De: FilesystemExplorerPropertiesPanel
    """
    AbstractDataStoreParametersPanel.setExcludeGeometryOptions(self,excludeGeometryOptions)
    self.enableComponents()
    
  def putParameters(self, parameters): # pylint: disable=R0912,R0915
    """
    Rellena los components del panel con los valores de parameters.
    De: FilesystemExplorerPropertiesPanel
    """
    saveAutorefresh = self._autorefresh
    self.setAutorefresh(False)

    self._parameters = parameters.getCopy()
    self.file = self._parameters.getDynValue("file")
    self.providerName = self._parameters.getDynValue("ProviderName")
    self.crs = self._parameters.getDynValue("CRS")
    if self.crs!=None:
      self.txtCRS.setText(self.crs.getAbrev())

    fieldsDefinition = parameters.getDynValue("fieldsDefinition")
    if fieldsDefinition!=None:
      self.rdbFixedSize.setSelected(True)
      self.rdbUseSeparator.setSelected(False)
    else:
      self.rdbFixedSize.setSelected(False)
      self.rdbUseSeparator.setSelected(True)
    
    self.chkIgnoreErrors.setSelected(parameters.getDynValue("ignoreErrors"))
    self.chkUseHeader.setSelected(parameters.getDynValue("firstLineHeader"))
    self.cboQuoteCharacter.setSelectedItem(parameters.getDynValue("quoteCharacter"))
    self.cboCharSet.setSelectedItem(parameters.getDynValue("charset"))
    self.setLocale(parameters.getDynValue("locale"))
    self.txtCommentStartMarker.setText(parameters.getDynValue("commentStartMarker"))
    self.txtEscapeCharacter.setText(parameters.getDynValue("escapeCharacter"))
    self.txtEscapeCharacter.setText(parameters.getDynValue("escapeCharacter"))

    delimiter = parameters.getDynValue("delimiter")
    if delimiter in ("", None):
      delimiter = ";"
    if delimiter == "," :
      self.rdbUseColon.setSelected(True)
    elif delimiter == ";" : 
      self.rdbUseSemiColon.setSelected(True)
    elif  delimiter == "\t" :
      self.rdbUseTab.setSelected(True)
    elif delimiter == " " :
      self.rdbUseSpace.setSelected(True)
    else: 
      self.rdbUseOther.setSelected(True)
      self.txtOtherSeparator.setText(delimiter)

    self.spnSkipFromLine.setValue(parameters.getDynValue("skipLines"))
    
    self.columnTypes.setHeader(parameters.getDynValue("header"),delimiter)
    self.columnTypes.setFixedFielDefinition(fieldsDefinition)

    self.txtGeomName.setText(parameters.getDynValue("pointColumnName"))
    pointColumns = parameters.getDynValue("point")
    if pointColumns!=None:
      x = pointColumns.split(",")
      l=len(x)
      if l>0 :
        self.cboColumnX.setSelectedItem(x[0])
        if l>1 :
          self.cboColumnY.setSelectedItem(x[1])
          if l>2 :
            self.cboColumnZ.setSelectedItem(x[2])
      self.rdbColumnsXYZ.setSelected(True)
      self.rdbWithoutGeometry.setSelected(False)
    else:
      self.cboColumnX.setSelectedItem("")
      self.cboColumnY.setSelectedItem("")
      self.cboColumnZ.setSelectedItem("")
      self.rdbColumnsXYZ.setSelected(False)
      self.rdbWithoutGeometry.setSelected(True)
      
    self.setAutorefresh(saveAutorefresh)

    self.updatePreview()

  def fetchParameters(self, parameters):
    """
    Rellena parameters con los valores del panel.
    De: FilesystemExplorerPropertiesPanel
    """
    if self.rdbUseColon.isSelected():
      delimiter = ","
    elif self.rdbUseSemiColon.isSelected():
      delimiter = ";"
    elif self.rdbUseTab.isSelected():
      delimiter = "\t"
    elif self.rdbUseSpace.isSelected():
      delimiter = " "
    elif self.rdbUseOther.isSelected():
      delimiter = self.txtOtherSeparator.getText()

    parameters.clear()
    parameters.setDynValue("file",self.file)
    parameters.setDynValue("ProviderName",self.providerName)
    parameters.setDynValue("ignoreErrors",self.chkIgnoreErrors.isSelected())
    parameters.setDynValue("firstLineHeader",self.chkUseHeader.isSelected())
    parameters.setDynValue("delimiter",delimiter)
    parameters.setDynValue("quoteCharacter",self.cboQuoteCharacter.getSelectedItem())
    parameters.setDynValue("commentStartMarker",self.txtCommentStartMarker.getText().strip())
    parameters.setDynValue("escapeCharacter",self.txtEscapeCharacter.getText().strip())
    parameters.setDynValue("skipLines",self.spnSkipFromLine.getValue())
    parameters.setDynValue("charset",self.cboCharSet.getSelectedItem())
    parameters.setDynValue("locale",self.cboLocale.getSelectedItem().getLocale().toLanguageTag())    
    parameters.setDynValue("header",self.columnTypes.getHeader(delimiter))
    if self.columnTypes.isFixedSize():
      parameters.setDynValue("fieldsDefinition",self.columnTypes.getFixedFielDefinition())

    if self.rdbColumnsXYZ.isSelected() :
      parameters.setDynValue("CRS", self.crs)
      columnX = self.cboColumnX.getSelectedItem()
      columnY = self.cboColumnY.getSelectedItem()
      columnZ = self.cboColumnZ.getSelectedItem()
      if columnX != None and columnY != None:
        pointColumns = columnX + "," + columnY
        if self.cboColumnZ.getSelectedItem() != None:
          if columnZ!=None and columnZ.strip() != "":
            pointColumns += "," + columnZ
        parameters.setDynValue("point",pointColumns)  
        parameters.setDynValue("pointColumnName",self.txtGeomName.getText())
      
    elif self.rdbWKTGeometry.isSelected():
      parameters.setDynValue("CRS", self.crs)
      columnGeometry = self.cboWKTGeometry.getSelectedItem()
      if columnGeometry!=None:
        parameters.setDynValue("geometry_column", columnGeometry)
    
    
  def updatePreview(self):
    self.fetchParameters(self._parameters)
    self._parameters.setDynValue("ignoreErrors",True)
    self._parameters.setDynValue("limit",100)
    dataManager = DALLocator.getDataManager()
    try:
      self.currentStore = dataManager.openStore("CSV",self._parameters)
    except Throwable, ex: # pylint: disable=W0612
      if self.featureTable!=None:
        self.featureTable.setVisible(False)
      self.currentStore = None
      self.columnTypes.clear()
      return

    saveAutorefresh = self._autorefresh
    self.setAutorefresh(False)
    DALSwingManager = DALSwingLocator.getSwingManager()

    tableModel = DALSwingManager.createFeatureTableModel(self.currentStore, None)
    self.featureTable = DALSwingManager.createJFeatureTable(tableModel)
    self.featureTable.setVisibleStatusbar(False)
    self.tableContainer.setLayout(BorderLayout())
    self.tableContainer.removeAll()
    self.tableContainer.add(self.featureTable, BorderLayout.CENTER)
    self.tableContainer.updateUI()
    self.featureTable.addColumnSelectionListener(ActionListenerAdapter(self.tablePreview_columnSelected))

    prevColumnX = self.cboColumnX.getSelectedItem()
    prevColumnY = self.cboColumnY.getSelectedItem()
    prevColumnZ = self.cboColumnZ.getSelectedItem()
    prevWKTGeometry = self.cboWKTGeometry.getSelectedItem()

    names = list()
    ft = self.currentStore.getDefaultFeatureType()
    for at in ft.getAttributeDescriptors():
      names.append(at.getName())

    if not prevColumnX in names :
      prevColumnX = None
    if not prevColumnY in names :
      prevColumnY = None
    if not prevColumnZ in names :
      prevColumnZ = None
    if not prevWKTGeometry in names :
      prevWKTGeometry = None
    
    self.columnTypes.setStore(self.currentStore)

    self.cboWKTGeometry.removeAllItems()
    self.cboColumnX.removeAllItems()
    self.cboColumnY.removeAllItems()
    self.cboColumnZ.removeAllItems()
    self.cboColumnZ.addItem(" ")

    for at in ft.getAttributeDescriptors():
      name = at.getName()
      self.featureTable.getModel().setColumnVisible(name,True)
      if at.getDataType().isNumeric():
        self.cboColumnX.addItem(name)
        if prevColumnX==None and name.lower() in ("x", "lon", "lo", "long", "longitud","longitude"):
          prevColumnX = name
        self.cboColumnY.addItem(name)
        if prevColumnY==None and name.lower() in ("y", "lat", "la", "latitude","latitud"):
          prevColumnY = name
        self.cboColumnZ.addItem(name)
        if prevColumnZ==None and name.lower() in ("z",):
          prevColumnZ = name
      elif at.getDataType().getType() in (DataTypes.STRING, DataTypes.GEOMETRY):
        self.cboWKTGeometry.addItem(name)
        if prevWKTGeometry==None:
          prevWKTGeometry = name
        
    self.cboColumnX.setSelectedItem(prevColumnX)
    self.cboColumnY.setSelectedItem(prevColumnY)
    self.cboColumnZ.setSelectedItem(prevColumnZ)
    self.cboWKTGeometry.setSelectedItem(prevWKTGeometry)

    self.featureTable.setVisible(True)
    self.setAutorefresh(saveAutorefresh)
  
  def enableComponents(self):
    useSeparator = self.rdbUseSeparator.isSelected()
    self.rdbUseTab.setEnabled(useSeparator)
    self.rdbUseColon.setEnabled(useSeparator)
    self.rdbUseSemiColon.setEnabled(useSeparator)
    self.rdbUseSpace.setEnabled(useSeparator)
    self.rdbUseOther.setEnabled(useSeparator)
    self.cboQuoteCharacter.setEnabled(useSeparator)
    self.txtEscapeCharacter.setEnabled(useSeparator)
    self.spnColumnsCount.setEnabled(not useSeparator)

    self.columnTypes.setFixedSize(not useSeparator)
    self.columnTypes.enableComponents()

    if self.rdbColumnsXYZ.isSelected():
      self.lblGeomName.setEnabled(True)
      self.txtGeomName.setEnabled(True)
      self.lblColumnX.setEnabled(True)
      self.lblColumnY.setEnabled(True)
      self.lblColumnZ.setEnabled(True)
      self.cboColumnX.setEnabled(True)
      self.cboColumnY.setEnabled(True)
      self.cboColumnZ.setEnabled(True)
      self.cboWKTGeometry.setEnabled(False)
      self.btnCRS.setEnabled(True)
      
    elif self.rdbWKTGeometry.isSelected():
      self.lblGeomName.setEnabled(False)
      self.txtGeomName.setEnabled(False)
      self.lblColumnX.setEnabled(False)
      self.lblColumnY.setEnabled(False)
      self.lblColumnZ.setEnabled(False)
      self.cboColumnX.setEnabled(False)
      self.cboColumnY.setEnabled(False)
      self.cboColumnZ.setEnabled(False)
      self.cboWKTGeometry.setEnabled(True)
      self.btnCRS.setEnabled(True)

    else:
      self.lblGeomName.setEnabled(False)
      self.txtGeomName.setEnabled(False)
      self.lblColumnX.setEnabled(False)
      self.lblColumnY.setEnabled(False)
      self.lblColumnZ.setEnabled(False)
      self.cboColumnX.setEnabled(False)
      self.cboColumnY.setEnabled(False)
      self.cboColumnZ.setEnabled(False)
      self.cboWKTGeometry.setEnabled(False)
      self.btnCRS.setEnabled(False)
    
    self.tabOptions.setEnabledAt(1,not self.getExcludeGeometryOptions())

  def autorefresh(self,secs=2):
    #print "autorefresh", self._autorefresh
    if self._autorefresh :
      self.timerAutorefresh.setRepeats(False)
      self.timerAutorefresh.setDelay(secs*1000)
      self.timerAutorefresh.restart()
    else:
      self.timerAutorefresh.stop()
    
  def tablePreview_columnSelected(self,*args):
    self.columnTypes.setCurrent(min(self.featureTable.getSelectedColumns()))

  def timerAutorefresh_perform(self, *args):
    #print "timerAutorefresh_perform", str(datetime.datetime.now())
    self.timerAutorefresh.setRepeats(False)
    self.timerAutorefresh.stop()
    self.updatePreview()

  def spnColumnsCount_change(self, *args):
    self.columnTypes.setColumnsCount(self.spnColumnsCount.getValue())
  
  def btnPreview_click(self, *args):
    self.updatePreview()

  def columnTypes_change(self,*args):
    self.autorefresh(4)
    
  def spnSkipFromLine_change(self,*args):
    self.autorefresh()
   
  def chkIgnoreErrors_change(self,*args):
    self.autorefresh()

  def chkUseHeader_change(self,*args):
    self.columnTypes.clear()
    self.autorefresh()

  def txtCommentStartMarker_change(self,*args):
    self.autorefresh(4)

  def rdbUseTab_change(self,*args):
    self.columnTypes.clear()
    self.enableComponents()
    self.autorefresh()
    
  def rdbUseColon_change(self,*args):
    self.columnTypes.clear()
    self.enableComponents()
    self.autorefresh()
    
  def rdbUseSemiColon_change(self,*args):
    self.columnTypes.clear()
    self.enableComponents()
    self.autorefresh()
    
  def rdbUseSpace_change(self,*args):
    self.columnTypes.clear()
    self.enableComponents()
    self.autorefresh()
    
  def rdbUseOther_change(self,*args):
    self.columnTypes.clear()
    self.enableComponents()
    self.autorefresh()
    
  def rdbUseSeparator_change(self,*args):
    self.columnTypes.clear()
    self.enableComponents()
    self.autorefresh(4)

  def rdbFixedSize_change(self,*args):
    self.columnTypes.clear()
    self.enableComponents()
    self.autorefresh(4)

  def rdbWithoutGeometry_change(self, *args):
    self.enableComponents()
    self.autorefresh(5)
    
  def rdbWKTGeometry_change(self, *args):
    self.enableComponents()
    self.autorefresh(5)
    
  def rdbColumnsXYZ_change(self, *args):
    self.enableComponents()
    self.autorefresh(5)

  def cboColumnX_change(self,*args):
    self.autorefresh(5)
  
  def cboColumnY_change(self,*args):
    self.autorefresh(5)
  
  def cboColumnZ_change(self,*args):
    self.autorefresh(5)
  
  def cboQuoteCharacter_change(self,*args):
    self.autorefresh()

  def btnCRS_click(self,*args):
    i18nManager = ToolsLocator.getI18nManager()
    title=i18nManager.getTranslation("_Select_the_reference_system")
    csSelect = CRSSelectPanelFactory.getUIFactory().getSelectCrsPanel(self.crs, True)
    ToolsSwingLocator.getWindowManager().showWindow(csSelect, title, WindowManager.MODE.DIALOG)
    if csSelect.isOkPressed():
      self.crs = csSelect.getProjection()
      self.txtCRS.setText(self.crs.getAbrev())
      self.autorefresh(2)

  def btnOptions_click(self,*args):
    p=self.btnOptions.getLocationOnScreen()
    self.mnuOptions.show(self.asJComponent(),0,0)
    self.mnuOptions.setLocation(p.x,p.y+self.btnOptions.getHeight())

  def mnuSaveParameters_click(self, *arsg):
    i18nManager = ToolsLocator.getI18nManager()
    title=i18nManager.getTranslation("_Save_parameters_as_XellipsisX")
    f = commonsdialog.filechooser(commonsdialog.SAVE_FILE,title)
    if f!=None and len(f)>0:
      self.fetchParameters(self._parameters)
      writer = ParametersIO()    
      writer.write(f[0],self._parameters)
    
    
  def mnuLoadParameters_click(self, *arsg):
    i18nManager = ToolsLocator.getI18nManager()
    title=i18nManager.getTranslation("_Load_parameters_from_XellipsisX")
    f = commonsdialog.filechooser(commonsdialog.OPEN_FILE,title)
    if f!=None and len(f)>0:
      reader = ParametersIO()    
      reader.read(f[0],self._parameters)
      self._parameters.setDynValue("file",self.file)
      self.putParameters(self._parameters)
    
  def mnuAutomaticPreview_click(self, *arsg):
    self.setAutorefresh(self.mnuAutomaticPreview.isSelected())

  def txtOtherSeparator_focusGained(self,*args):
    self.txtOtherSeparator.selectAll()
    
  def txtEscapeCharacter_focusGained(self,*args):
    self.txtEscapeCharacter.selectAll()
    
  def txtCommentStartMarker_focusGained(self,*args):
    self.txtCommentStartMarker.selectAll()
    
  def txtGeomName_focusGained(self,*args):
    self.txtGeomName.selectAll()
    

def main(*args):
  dataManager = DALLocator.getDataManager()
  parameters = dataManager.createStoreParameters("CSV")
  factory = CSVWizardFactory()
  fname = "test-fixedsize-latlon-en.txt"
  fname = "test-latlon-es.csv"
  #fname = "test-nogeom.csv"
  fname = "test-XYZ-en.csv"
  fname = "muchas_columnas.csv"
  
  parameters.setDynValue("file",getResource(__file__,"data",fname))
  wizard = factory.create(parameters)
  wizard.setExcludeGeometryOptions(False)
  wizard.showWindow("CSV Wizard")
