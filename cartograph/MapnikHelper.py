from lxml import etree as ET

class MapnikHelper:
    def __init__(self):
        self.styles = []
        self.layers = []

    def load(self, path):
        self.styles = []
        self.layers = []
        self.merge(path)

    def merge(self, path):
        root = ET.parse(path).getroot()
        for child in list(root):
            root.remove(child)
            if child.tag == 'Layer':
                self.layers.append(child)
            elif child.tag == 'Style':
                self.styles.append(child)
            else:
                raise Exception, 'Unknown tag: ' + child.tag

    def mkRoot(self):
        root = ET.Element('Map')
        root.set('srs', "+init=epsg:3857")
        root.set('background-color', "rgb(0,0,0,0)")
        return root

    def mkStyle(self, name):
        st = ET.Element("Style", name=name)
        self.styles.append(st)
        return st

    def mkPGLayer(self, conf, name, table, styleNames):
        l = ET.Element("Layer", srs="+init=epsg:4236", name=name)
        l.set('cache-features', 'true')
        for n in styleNames:
            ET.SubElement(l, 'StyleName').text = n
        ds = ET.SubElement(l, 'Datasource')
        ET.SubElement(ds, 'Parameter', name='dbname').text = conf.get('PG', 'database')
        ET.SubElement(ds, 'Parameter', name='host').text = conf.get('PG', 'host')
        ET.SubElement(ds, 'Parameter', name='max_async_connection').text = '4'
        ET.SubElement(ds, 'Parameter', name='table').text = table
        ET.SubElement(ds, 'Parameter', name='type').text = 'postgis'
        self.layers.append(l)
        return l

    def write(self, path):
        root = self.mkRoot()
        root.extend(self.styles + self.layers)
        et = ET.ElementTree(root)
        et.write(path, encoding='UTF-8', pretty_print=True)





