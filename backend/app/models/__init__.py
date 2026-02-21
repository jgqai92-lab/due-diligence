from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.cached_financials import CachedFinancial  # noqa: E402, F401
from app.models.analysis_reports import AnalysisReport  # noqa: E402, F401
from app.models.holdings import Holding  # noqa: E402, F401
from app.models.alerts import Alert  # noqa: E402, F401
from app.models.watchlist import Watchlist  # noqa: E402, F401
from app.models.alert_settings import AlertSettings  # noqa: E402, F401
from app.models.workflow import WorkflowRun, WorkflowStep  # noqa: E402, F401
from app.models.ist import (  # noqa: E402, F401
    ISTScreen,
    ISTClaim,
    ISTBottleneck,
    ISTDemandModel,
    ISTValidation,
    ISTEquityCandidate,
    ISTEffectsChain,
    ISTDialecticReview,
    ISTMasterScreen,
    ISTRotationStrategy,
    ISTCatalystCalendar,
    ISTStressTest,
    ISTReport,
)
from app.models.ist_synthesis import (  # noqa: E402, F401
    ISTSynthesis,
    ISTSynthesisSource,
    ISTSynthesisEquity,
    ISTSynthesisDialectic,
)
from app.models.ist_refresh import ISTScreenRefresh  # noqa: E402, F401
from app.models.hfrt import (  # noqa: E402, F401
    HFRTProject,
    HFRTTemplate,
    HFRTSECFiling,
    HFRTDialecticReview,
)
from app.models.persona import PersonaAnalysis  # noqa: E402, F401
