"""Historia académica simulada para los certificados.

El prototipo no se conecta a ningún sistema académico real. Cada estudiante recibe
una historia ficticia pero estable (la misma cada vez), derivada de su id.
"""

import random
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# (código, nombre, nombre en inglés, créditos, contenido, contenido en inglés)
COURSES = [
    (
        "2555100",
        "Cálculo diferencial",
        "Differential Calculus",
        4,
        "Funciones reales, límites y continuidad, derivadas y sus aplicaciones, optimización.",
        "Real functions, limits and continuity, derivatives and their applications, optimization.",
    ),
    (
        "2555101",
        "Álgebra lineal",
        "Linear Algebra",
        3,
        "Sistemas de ecuaciones lineales, matrices, determinantes, espacios vectoriales, "
        "valores y vectores propios.",
        "Systems of linear equations, matrices, determinants, vector spaces, eigenvalues and "
        "eigenvectors.",
    ),
    (
        "2555102",
        "Lógica y algoritmos",
        "Logic and Algorithms",
        3,
        "Lógica proposicional, diseño de algoritmos, estructuras de control y pseudocódigo.",
        "Propositional logic, algorithm design, control structures and pseudocode.",
    ),
    (
        "2555200",
        "Cálculo integral",
        "Integral Calculus",
        4,
        "Integral definida e indefinida, técnicas de integración, series y sucesiones.",
        "Definite and indefinite integrals, integration techniques, series and sequences.",
    ),
    (
        "2555201",
        "Física mecánica",
        "Mechanical Physics",
        4,
        "Cinemática, leyes de Newton, trabajo y energía, momento lineal, rotación de cuerpos "
        "rígidos.",
        "Kinematics, Newton's laws, work and energy, linear momentum, rigid body rotation.",
    ),
    (
        "2555202",
        "Programación orientada a objetos",
        "Object-Oriented Programming",
        4,
        "Clases y objetos, encapsulamiento, herencia, polimorfismo, manejo de excepciones.",
        "Classes and objects, encapsulation, inheritance, polymorphism, exception handling.",
    ),
    (
        "2555300",
        "Estructuras de datos",
        "Data Structures",
        4,
        "Listas, pilas, colas, árboles, grafos, tablas hash y análisis de complejidad.",
        "Lists, stacks, queues, trees, graphs, hash tables and complexity analysis.",
    ),
    (
        "2555301",
        "Matemáticas discretas",
        "Discrete Mathematics",
        3,
        "Conjuntos, relaciones, inducción, combinatoria y teoría de grafos.",
        "Sets, relations, induction, combinatorics and graph theory.",
    ),
    (
        "2555302",
        "Probabilidad y estadística",
        "Probability and Statistics",
        3,
        "Probabilidad, variables aleatorias, distribuciones, estimación y pruebas de hipótesis.",
        "Probability, random variables, distributions, estimation and hypothesis testing.",
    ),
    (
        "2555400",
        "Bases de datos",
        "Databases",
        4,
        "Modelo entidad-relación, modelo relacional, normalización, SQL y transacciones.",
        "Entity-relationship model, relational model, normalization, SQL and transactions.",
    ),
    (
        "2555401",
        "Ingeniería de software",
        "Software Engineering",
        4,
        "Requisitos, diseño, metodologías ágiles, pruebas y gestión de proyectos de software.",
        "Requirements, design, agile methodologies, testing and software project management.",
    ),
    (
        "2555402",
        "Sistemas operativos",
        "Operating Systems",
        3,
        "Procesos e hilos, planificación, memoria, sistemas de archivos y concurrencia.",
        "Processes and threads, scheduling, memory, file systems and concurrency.",
    ),
]

TERMS = ["2023-1", "2023-2", "2024-1", "2024-2", "2025-1", "2025-2"]


@dataclass
class CourseRecord:
    code: str
    name: str
    credits: int
    term: str
    grade: Decimal
    content: str


def academic_record(student, language="es"):
    """Lista de cursos aprobados (ficticios) del estudiante, en orden cronológico."""
    rng = random.Random(f"tramite-claro-{student.pk}")
    count = rng.randint(7, 10)
    records = []
    for index, course in enumerate(COURSES[:count]):
        code, name, name_en, credits, content, content_en = course
        grade = Decimal(rng.randint(32, 50)) / 10
        records.append(
            CourseRecord(
                code=code,
                name=name_en if language == "en" else name,
                credits=credits,
                term=TERMS[min(index // 2, len(TERMS) - 1)],
                grade=grade,
                content=content_en if language == "en" else content,
            )
        )
    return records


def weighted_average(records):
    credits = sum(r.credits for r in records)
    if not credits:
        return None
    total = sum(r.grade * r.credits for r in records) / credits
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
