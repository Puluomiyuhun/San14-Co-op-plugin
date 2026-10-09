"""Native-refresh bootstrap bridge only; no ReceivedApply/protocol successor."""
from b_warm_bootstrap import BootstrapRulesBridge as PreviousBootstrap
from b_warm_refresh_rules_bridge import WarmRulesBridge


class BootstrapRulesBridge(PreviousBootstrap,WarmRulesBridge):
    """Keep exact old A->B lifecycle; use refresh for first and later banks.

    MRO intentionally places the new WarmRulesBridge after PreviousBootstrap:
    the predecessor's second-bank super().replace reaches the refresh loader.
    Its first-generation rule validation/restoration/rebinding is unchanged.
    """
    def _load_first(self,request,profile,source):
        return self._load_checkpoint(request,profile,source,0)
