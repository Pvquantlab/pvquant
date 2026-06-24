"""
PVQuant - Model Registry
========================

Tüm mevcut modelleri kaydeder ve isimle erişim sağlar.

Yeni model eklemek:
    ModelRegistry.register("model_adi", ModelClass)

Model kullanmak:
    ModelClass = ModelRegistry.get("barhdadi_bennis")
    model = ModelClass(plant=my_plant)
"""

from __future__ import annotations

from typing import Type

from .protocol import PVModel


class ModelNotFoundError(Exception):
    """Registry'de olmayan bir model çağrıldığında."""
    pass


class ModelAlreadyRegisteredError(Exception):
    """Aynı isimle ikinci kez kayıt denenirse."""
    pass


class ModelRegistry:
    """
    Tüm PV modellerinin merkezi kayıt defteri.

    Class-level state kullanır (singleton pattern).
    İmport zamanında modeller register edilir, sonra her yerden erişilebilir.
    """

    _registry: dict[str, Type[PVModel]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        model_class: Type[PVModel],
        overwrite: bool = False,
    ) -> None:
        """
        Bir model sınıfını registry'e ekle.

        Args:
            name: Modelin benzersiz adı, örn: "barhdadi_bennis"
            model_class: PVModel protocol'üne uyan sınıf
            overwrite: True ise mevcut kayıt üzerine yazar (testler için)

        Raises:
            ModelAlreadyRegisteredError: name zaten varsa ve overwrite=False
        """
        if name in cls._registry and not overwrite:
            raise ModelAlreadyRegisteredError(
                f"Model '{name}' zaten kayıtlı. "
                f"Üzerine yazmak için overwrite=True kullan."
            )
        cls._registry[name] = model_class

    @classmethod
    def get(cls, name: str) -> Type[PVModel]:
        """
        Kayıtlı bir model sınıfını isimle al.

        Args:
            name: Modelin kayıt adı

        Returns:
            Model sınıfı (örnek değil, sınıfın kendisi)

        Raises:
            ModelNotFoundError: Bu isimde kayıt yoksa
        """
        if name not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys())) or "(boş)"
            raise ModelNotFoundError(
                f"Model '{name}' kayıtlı değil. "
                f"Mevcut modeller: {available}"
            )
        return cls._registry[name]

    @classmethod
    def list_available(cls) -> list[str]:
        """Kayıtlı tüm model isimlerini alfabetik olarak döner."""
        return sorted(cls._registry.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Bir modelin kayıtlı olup olmadığını kontrol eder."""
        return name in cls._registry

    @classmethod
    def unregister(cls, name: str) -> None:
        """
        Bir modeli registry'den kaldırır. Genelde testler için.

        Args:
            name: Kaldırılacak modelin adı

        Raises:
            ModelNotFoundError: Bu isimde kayıt yoksa
        """
        if name not in cls._registry:
            raise ModelNotFoundError(f"Model '{name}' kayıtlı değil.")
        del cls._registry[name]

    @classmethod
    def clear(cls) -> None:
        """
        Tüm registry'i temizler. SADECE testler için.
        Production'da asla kullanılmamalı.
        """
        cls._registry.clear()