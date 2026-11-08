# TUBS LaTeX CD lite

This is the fresh, new design for the TU Braunschweig LaTeX templates in corporate design.
This readme is provided in both the git repository as well as the overleaf version. It is there to give a project overview, for a content overview please refer to the handbook.

## Description

The templates provide an environment for all things TU Braunschweig corporate design for LaTeX. We provide a class tubscd that defines all design elements of [the corporate design toolbox](https://www.tu-braunschweig.de/presse/corporate-design/cd-toolbox) in LaTeX. We also provide templates for the "Geschäftsausstattung", as well as templates for uni work submissions like bachelor thesises.

As of May 2025 this is the official home of the templates, the old templates can be found [here](https://git.rz.tu-bs.de/tubslatex/tubslatex) should there be the need to look them up again.
The old templates are not maintained anymore.

## Installation

There are two ways of installing the templates. The prefered and simple way is to copy the [read-only overleaf project](https://www.overleaf.com/read/hrydddhrkpvs#ab477b) to make your own, personally owned, writable copy.
You can also download this repository. There is no installation script that needs to be executed. You only need LaTeX on your system, the `compiler LuaLaTex` and the following common packages:
- etoolbox
- kvoptions
- silence
- fontspec
- lmodern
- xcolor
- xkeyval
- pgf
- tikz
- calc
- xstring
- ifthen
- babel

I assume they should come with the standard LaTeX installation, but testing is yet to be done. Feedback is welcome.

Some more packages might be requiered for special templates but they too should be common packages.

## Support

Generally, please contact the [HiWi directly with an email](mailto:tubs-latex@tu-braunschweig.de) if you need support.
Additionally, if you find errors or have helpful additions to the templates, please open an issue for all to see.

## Roadmap

There are still a bunch of things on the todo-list:

- logos/
  - [x] collect some FK1 institute logos for a start
- templates/
  - Abschlussarbeiten
    - [x] check BA content with Prüfungsamt
    - [x] check MA content wiith Prüfungsamt
    - [x] check Dissertation content with Prüfungsamt
    - [x] implement BA
    - [x] implement MA
    - [x] implement Dissertation
    - [x] implement simple submission
  - Geschäftsausstattung
    - [ ] Flyer
    - [ ] Brochueren
    - [x] Briefbogen Standard
    - [x] Briefbogen Digital
    - [x] Fax / Kurzbrief
    - [ ] Grusskarte
 - Plakate/
   - [x] Aushang
   - [ ] Poster / Wiss. Plakat
   - [x] Veranstaltungsplakat
 - [x] Beamer
- tubsCD/
  - [x] implement beamer
  - [x] implement CD colors
  - [x] implement fonts
  - [x] implement gaussian layout
  - [ ] implement Poster / Modullayout
  - [x] implement senderspace
  - [x] implement template connection
  - [x] implement banner loader
- [x] write example
- [x] write handbook
  - [ ] update & restructure handbook for better reading experience
- [x] update handbook when everything is implemented
- [ ] local installation testing

This list is not ordered.

## Contributing

The project is open to contributions. Please keep in mind that the main focus is on providing the corporate design. Everything else is secondary. We also try to provide universal templates so if you want to contribute something specific, please consider if it can be used in other parts of the university context.

## Authors and acknowledgment

Current authors:  Henry Behrend
Previous authors: Veronika Hille (2024-2026)

Autors of the previous templates until november 2020: Enrico Jörns, Tobias Rad, Martin Bäker, Philip Hönnecke et al.

## TU Braunschweig LaTeX Template License

**Effective Date:** 2025-06-01  
**Licensor:** Technische Universität Braunschweig, Stabsstelle für Presse und Kommunikation

### 1. Definitions
1. “Templates” means all LaTeX class (`.cls`), style (`.sty`), and supporting files provided by the Licensor.  
2. “Internal Code” means the original source files and build scripts.  
3. “Compiled Results” means any output (PDF, DVI, HTML) generated from the Templates.

### 2. Grant of License
Subject to the terms below, Licensor hereby grants to all current students and employees of TU Braunschweig a worldwide, non-exclusive, royalty-free license to:
- Use, copy and modify the Templates for any university-related work.
- Create and distribute Compiled Results under the “Rules for Publication and Distribution” of TU Braunschweig.

### 3. Conditions & Restrictions
- **Internal Code** may **not** be distributed or published outside of TU Braunschweig’s internal networks or repositories.
- All copies of Templates or modified versions **must** retain the following notice:
  > © 2025 Technische Universität Braunschweig – Stabsstelle für Presse und Kommunikation

### 4. No Warranty
The Templates are provided “as is,” without warranty of any kind. Licensor shall not be liable for any damages arising out of your use.

### 5. Termination
This license terminates automatically if you breach any term herein. After termination, you must cease all use and distribution of the Templates.

### 6. Governing Law
This Agreement is governed by the laws of the Federal Republic of Germany.

---

For questions or permission beyond the scope above, please contact  
**Stabsstelle für Presse und Kommunikation**  
Technische Universität Braunschweig  
E-Mail: presse@tu-braunschweig.de

## Project status
Work in progress.
