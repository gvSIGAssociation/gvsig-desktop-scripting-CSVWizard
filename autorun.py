
import gvsig
from gvsig.libs.formpanel import getResource

from java.io import File
from org.gvsig.tools import ToolsLocator

from addons.CSVWizard.CSVWizard import CSVWizardFactory 
#from CSVWizard import CSVWizardFactory

def main(*args):
  factory = CSVWizardFactory()
  factory.selfRegister()

  i18nManager = ToolsLocator.getI18nManager()
  i18nManager.addResourceFamily("text",File(getResource(__file__,"i18n")))
  

