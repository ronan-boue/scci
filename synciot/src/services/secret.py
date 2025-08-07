"""
https://learn.microsoft.com/en-us/python/api/azure-keyvault-secrets/azure.keyvault.secrets.secretclient?view=azure-python
https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential?view=azure-python

"""
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# ------------------------------------------------------------------------------
#
class Secret:
    # --------------------------------------------------------------------------
    #
    def __init__(self):
        self.credential = None
        self.client = None

    # --------------------------------------------------------------------------
    #
    def init(self, config):
        try:

            key_vault_config = config.get("key_vault", {})
            self.vault_url = key_vault_config.get("url")

            # Validate configuration
            if not all([self.vault_url]):
                raise ValueError("Key Vault configuration is incomplete in the config file.")

            # Create a credential and SecretClient
            self.credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=self.credential)

        except Exception as e:
            raise RuntimeError(f"Failed to configure secret client '{self.vault_url}': {e}")

    # --------------------------------------------------------------------------
    #
    def get_secret(self, secret_name):
        """
        Retrieve a secret from Azure Key Vault.

        :param secret_name: Name of the secret to retrieve.
        :return: The value of the secret.
        """
        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve secret '{secret_name}': {e}")
