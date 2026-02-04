from abc import abstractmethod


class FileStore:
    @abstractmethod
    def write(self, path: str, contents: str | bytes, public: bool = False) -> None:
        """Write contents to a file at the given path.

        Args:
            path: The path where the file should be stored.
            contents: The content to write (string or bytes).
            public: If True, make the file publicly accessible (for cloud storage).
                   For local/memory stores, this parameter is ignored.
        """
        pass

    @abstractmethod
    def read(self, path: str) -> str:
        pass

    @abstractmethod
    def list(self, path: str) -> list[str]:
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        pass

    def get_public_url(self, path: str) -> str | None:
        """Get the public URL for a file.

        Returns the public URL if the file is publicly accessible,
        or None if public URLs are not supported by this store.

        Args:
            path: The path to the file.

        Returns:
            The public URL string, or None if not supported.
        """
        return None
