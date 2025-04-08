from oidc_provider.lib.claims import ScopeClaims

from .models import NYUUser


class OsirisScopeClaims(ScopeClaims):
    def scope_nyu(self):
        """
        This method is called when the scope 'nyu' is requested.
        """
        try:
            nyu_user = NYUUser.objects.get(user=self.user)
            claims = {
                'netid': nyu_user.netid,
                'first_name': nyu_user.first_name,
                'last_name': nyu_user.last_name,
                'affiliation': nyu_user.affiliation,
            }
            return claims
        except NYUUser.DoesNotExist:
            return {}
