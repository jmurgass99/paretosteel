"""paretosteel.section_bridge
================================
Puente bidireccional puro de datos entre ParetoSteel y el modelo canónico (fastsap / jmstructural-common).

Permite:
1. Leer las secciones actualmente asignadas a cada barra de un `Model`.
2. Asignar secciones optimizadas propuestas a las barras del `Model`.
3. Validar defensivamente contra `fastsap.section_catalog` las secciones propuestas.
"""
from __future__ import annotations
from typing import Mapping, Sequence

from paretosteel._common.model import Element, Model, SectionRef


def read_assigned_sections(model: Model) -> dict[str, SectionRef]:
    """Lee el mapeo {element_id: SectionRef} de un modelo canónico."""
    return {el.id: el.section for el in model.elements}


def apply_proposed_sections(
    model: Model,
    proposed_sections: Mapping[str, str | SectionRef],
    validate_against_catalog: bool = True,
) -> Model:
    """Aplica las secciones propuestas a los elementos del modelo.

    Args:
        model: Instancia inmutable de Model canónico.
        proposed_sections: Diccionario {element_id: nombre_seccion o SectionRef}.
        validate_against_catalog: Si es True, verifica la existencia en fastsap.section_catalog
            (requiere el paquete ``fastsap``, que no es dependencia de paretosteel). Con False
            el puente funciona sin fastsap y no valida nada contra catálogo.

    Returns:
        Nueva instancia inmutable de Model con las secciones actualizadas.
    """
    # fastsap solo hace falta para VALIDAR: importarlo siempre hacía que
    # validate_against_catalog=False fallase con ModuleNotFoundError sin fastsap.
    if validate_against_catalog:
        from fastsap.section_catalog import get_section

    new_elements: list[Element] = []
    seen_sections: dict[str, SectionRef] = {s.name: s for s in model.sections}

    for el in model.elements:
        if el.id in proposed_sections:
            prop = proposed_sections[el.id]
            if isinstance(prop, SectionRef):
                sec_ref = prop
            else:
                sec_name = str(prop)
                # Determinar familia heurística o por catálogo
                sec_ref = SectionRef(name=sec_name, family="I" if sec_name.startswith(("IPE", "HEB", "HEA", "HEM", "UB", "UC")) else "OTHER")

            if validate_against_catalog:
                try:
                    get_section(sec_ref.name)
                except Exception as e:
                    raise ValueError(f"La sección propuesta '{sec_ref.name}' para el elemento '{el.id}' no existe en el catálogo o carece de propiedades: {e}")

            new_el = Element(
                id=el.id,
                node_i=el.node_i,
                node_j=el.node_j,
                section=sec_ref,
                material=el.material,
                rotation_deg=el.rotation_deg,
            )
            new_elements.append(new_el)
            seen_sections[sec_ref.name] = sec_ref
        else:
            new_elements.append(el)

    return Model(
        nodes=model.nodes,
        restraints=model.restraints,
        materials=model.materials,
        sections=tuple(seen_sections.values()),
        elements=tuple(new_elements),
        patterns=model.patterns,
        nodal_loads=model.nodal_loads,
        element_loads=model.element_loads,
        mass_source=model.mass_source,
        cases=model.cases,
        reactions=model.reactions,
    )


__all__ = ["read_assigned_sections", "apply_proposed_sections"]
