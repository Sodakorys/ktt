import setuptools
import versioneer

with open("README.md", "r") as fh:
    long_description = fh.read()
with open("requirements.txt", "r") as fh:
    requirements = [line.strip() for line in fh]

setuptools.setup(
    name="korys tester tools",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="Soufian Mouaouiya",
    author_email="soufian.mouaouiya@korys.io",
    description="A python toolbox for writing tests and reports.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    install_requires=requirements,
)

