
import gvsig
import xmltodic
 
class ParametersIO(object):

  def __init__(self):
    pass

  def write(self,fname, parameters):
    getAbsolutePath = getattr(fname, "getAbsolutePath",None)
    if getAbsolutePath!=None:
      fname = getAbsolutePath()
    
    fout = open(fname,"w")
    fout.write("<parameters>\n")
    fields = parameters.getDynClass().getDynFields()
    for field in fields:
      if field.isPersistent():
        name = field.getName()
        value = parameters.getDynValue(name)
        if value == None:
          value = ""
        fout.write("  <%s>%s</%s>\n" % (name,value,name) )
    fout.write("</parameters>\n")
    fout.close()

  def read(self, fname, parameters):
    getAbsolutePath = getattr(fname, "getAbsolutePath",None)
    if getAbsolutePath!=None:
      fname = getAbsolutePath()
    fin = open(fname,"r")
    d = xmltodic.parse(fin)
    p = d["parameters"]
    for k,v in p.items():
      parameters.setDynValue(k,v)
      
  