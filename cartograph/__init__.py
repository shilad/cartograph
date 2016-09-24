# Exposed for the external API
import matplotlib

matplotlib.use("Agg")

import Config

from server.VectorServer import Server

# Expose public Luigi tasks:

from Choropleth import AllChoropleth
from Coordinates import CreateEmbedding, CreateFullAnnoyIndex, CreateSampleAnnoyIndex, CreateSampleCoordinates
from Denoiser import Denoise
from FastKnn import FastKnn
from Contour import CreateContours
from CalculateZooms import ZoomLabeler
from BorderGeoJSONWriter import CreateContinents, BorderGeoJSONWriter
from Labels import LabelMapUsingZoom
from Edges import CreateCoordinateEdges
from MapStyler import CreateMapXml
from PopularityLabelSizer import PopularityLabelSizerCode
from PreReqs import ArticlePopularity, LabelNames, SampleCreator, WikiBrainNumbering, EnsureDirectoriesExist
from Regions import MakeRegions, MakeSampleRegions
# from RenderMap import RenderMap
from TopTitlesGeoJSONWriter import TopTitlesGeoJSONWriter
from ZoomGeoJSONWriter import ZoomGeoJSONWriter, CreateLabelsFromZoom
from Edges import LoadCoordinateEdges
from ParentTasks import ParentTask
from Utils import read_features

