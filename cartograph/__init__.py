# Exposed for the external API
import matplotlib

matplotlib.use("Agg")

import Config

# Expose public Luigi tasks:

from Choropleth import AllChoropleth
from Coordinates import CreateEmbedding, CreateFullAnnoyIndex, CreateSampleAnnoyIndex, CreateSampleCoordinates
from Denoiser import Denoise
from FastKnn import FastKnn
from Contour import CreateContours
from BorderGeoJSONWriter import CreateContinents, BorderGeoJSONWriter
from Edges import CreateCoordinateEdges
from MapStyler import CreateMapXml
from PreReqs import ArticlePopularity, LabelNames, SampleCreator, WikiBrainNumbering, EnsureDirectoriesExist
from Regions import MakeRegions, MakeSampleRegions
from Edges import LoadCoordinateEdges
from ParentTasks import ParentTask
from Utils import read_features

