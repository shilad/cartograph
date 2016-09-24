import luigi
import Config
import Colors

from lxml import etree as ET

from LuigiUtils import MTimeMixin, TimestampedLocalTarget
from PGLoader import LoadCoordinates, LoadCountries
from PGLoader import LoadContoursDensity, LoadContoursCentroid

from cartograph import AllChoropleth
from cartograph.MapnikHelper import MapnikHelper


class MapStylerCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


class CreateMapXml(MTimeMixin, luigi.Task):
    colorWheel = Config.getColorWheel()

    '''
    Creates the mapnik map.xml configuration file and renders png and svg
    images of the map for visual reference to make sure code excuted properly.
    Map png and svg can be found in ./data/images
    '''
    def output(self):
        config = Config.get()
        mapDir = config.get('DEFAULT', 'mapDir')
        paths = [ mapDir + '/base.xml' ]
        for name in config.get('Metrics', 'active').split():
            paths.append('%s/%s.xml' % (mapDir, name))
        return [TimestampedLocalTarget(p) for p in paths]

    def requires(self):
        return (
            LoadContoursDensity(),
            LoadContoursCentroid(),
            LoadCoordinates(),
            LoadCountries(),
            MapStylerCode(),
            Colors.ColorsCode(),
            AllChoropleth(),
        )

    def run(self):
        config = Config.get()
        mapDir = config.get('DEFAULT', 'mapDir')

        m = MapnikHelper()
        self.makeCountries(config, m)
        self.makeContours(config, m)
        m.write(mapDir + '/base.xml')

        for name in config.get('Metrics', 'active').split():
            m = MapnikHelper()
            self.makeCountries(config, m)
            self.makeContours(config, m)
            m.merge(mapDir + '/' + name + '_only.xml')
            m.write(mapDir + '/' + name + '.xml')

    def makeCountries(self, config, m):
        numClusters = config.getint("PreprocessingConstants", "num_clusters")
        styles = []
        for i in range(numClusters):
            n = 'cluster_' + str(i)
            styles.append(n)
            s = m.mkStyle(n)
            r = ET.SubElement(s, 'Rule')
            f = ET.SubElement(r, 'Filter').text = '[clusterid].match("' + str(i) + '")'

            p = ET.SubElement(r, 'PolygonSymbolizer')
            p.set('fill', self.colorWheel[str(i)][7])
            # p.set('fill_opacity', '1.0')

            l = ET.SubElement(r, 'LineSymbolizer')
            l.set('stroke', '#444')
            # l.set('stroke_opacity', '1.0')
            # l.set('stroke_width', '2')

        m.mkPGLayer(config, 'countries', 'countries', styles)

    def makeContours(self, config, m):
        numContours = config.getint("PreprocessingConstants", "num_contours")
        numClusters = config.getint("PreprocessingConstants", "num_clusters")
        styles = []
        for i in range(numClusters):
            for j in range(numContours):
                n = 'contour_%d_%d' % (i, j)
                s = m.mkStyle(n)
                r = ET.SubElement(s, 'Rule')
                f = ET.SubElement(r, 'Filter').text = '[contourid].match("%s_%s")' % (i, j)
                p = ET.SubElement(r, 'PolygonSymbolizer')
                p.set('fill', self.colorWheel[str(i)][j])
                # p.set('fill_opacity', '1.0')
                p.set('gamma', '1.0')
                styles.append(n)
        m.mkPGLayer(config, 'contours', 'contourscentroid', styles)
