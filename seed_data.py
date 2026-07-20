"""
Generate sample data per the Excel schema instructions.

Produces 50 budgets, 50 projects, 50 risks, 50 architecture components,
50 run contracts, and edges linking them together.
"""

import random
from datetime import date, timedelta

random.seed(42)

BUDGET_STATUSES = (
    "Proposed",
    "Budget agreed",
    "in flight",
    "Budget not agreed",
    "Completed",
    "Cancelled",
)
BUDGET_CATEGORIES = ("Licenses/Support", "Cloud", "Project")
SPEND_TYPES = ("KTLO", "Expand", "Major Change")

RISK_RESPONSES = ("Accept", "Mitigate")
RISK_STATUSES = ("Open", "Closed")
RISK_CATEGORIES = ("Security", "Commercial", "Personnel")
PROXIMITY_BANDS = (
    "Immediate Term: 0 - 6 Months",
    "Recurrent",
    "Short Term: 7-12 Months",
    "Medium Term: 13 - 36 Months",
    "Long Term: >36 Months",
)
LIKELIHOODS = (
    "To Be Determined",
    "Unlikely: <11%",
    "Less Likely: 11-39%",
    "Mid-Likelihood: 40-60%",
    "Likely: 61-89%",
    "Almost Certain: 90-100%",
)
IMPACT_BANDS = (
    "To Be Determined",
    "Low: £1 - <£10M",
    "Medium: £10M - <£20M",
    "High: £20M - <£50M",
    "Very High: £50M - <£100M",
    "Severe: £100M+",
)

ARCH_OUTLOOKS = ("Retain", "Upgrade", "Decommission")
DEPLOYMENT_STATES = (
    "Not yet deployed",
    "Live",
    "Awaiting Decommissioning",
    "Decommissioned",
)
CLASS_OF_SERVICE = ("Level 1", "Level 2", "Level 3", "Level 4")
HOST_TYPES = ("On Prem", "Private Cloud", "Vendor Cloud", "Public Cloud")

SERVICE_TYPES = (
    "Software & Managed Service",
    "Support",
    "Software",
    "Managed Service",
    "Professional Services",
)
CONTRACT_STATUSES = ("Archive", "Current")

RENAISSANCE_ARTISTS = (
    "Leonardo da Vinci",
    "Michelangelo",
    "Raphael",
    "Donatello",
    "Titian",
    "Caravaggio",
    "Botticelli",
    "Brunelleschi",
    "Giotto",
    "Masaccio",
)

ASTRONAUTS = (
    "Neil Armstrong",
    "Buzz Aldrin",
    "Yuri Gagarin",
    "Valentina Tereshkova",
    "Sally Ride",
    "Chris Hadfield",
    "Mae Jemison",
    "John Glenn",
    "Alan Shepard",
    "Peggy Whitson",
)

CARTOON_CHARACTERS = (
    "Bugs Bunny",
    "Daffy Duck",
    "Scooby-Doo",
    "Fred Flintstone",
    "Homer Simpson",
    "SpongeBob SquarePants",
    "Tom Cat",
    "Jerry Mouse",
    "Popeye",
    "Woody Woodpecker",
)

FOOTBALL_PLAYERS = (
    "Lionel Messi",
    "Cristiano Ronaldo",
    "Kylian Mbappé",
    "Erling Haaland",
    "Neymar Jr",
    "Kevin De Bruyne",
    "Luka Modrić",
    "Harry Kane",
    "Mohamed Salah",
    "Vinícius Júnior",
)

TENNIS_PLAYERS = (
    "Roger Federer",
    "Rafael Nadal",
    "Novak Djokovic",
    "Serena Williams",
    "Steffi Graf",
    "Pete Sampras",
    "Martina Navratilova",
    "Björn Borg",
    "Billie Jean King",
    "Rod Laver",
)

ARCH_NAMES = (
    "Customer Portal",
    "Payment Gateway",
    "Identity Broker",
    "Data Lake",
    "Event Hub",
    "API Gateway",
    "CRM Connector",
    "Reporting Engine",
    "Workflow Orchestrator",
    "Document Store",
    "Search Index",
    "Notification Service",
    "Audit Trail",
    "Secrets Vault",
    "Load Balancer",
    "Cache Cluster",
    "Message Queue",
    "Batch Scheduler",
    "Analytics Platform",
    "Mobile Backend",
)

PROJECT_TITLES = (
    "Platform Modernisation",
    "Cloud Migration Wave",
    "Security Hardening",
    "Customer Experience Refresh",
    "Data Platform Upgrade",
    "Integration Hub Delivery",
    "Legacy Decommission",
    "Mobile App Enhancement",
    "Automation Programme",
    "Compliance Remediation",
)

RISK_NAMES = (
    "Third-party dependency failure",
    "Regulatory non-compliance exposure",
    "Key person dependency",
    "Cyber security breach",
    "Budget overrun risk",
    "Vendor contract lapse",
    "Data quality degradation",
    "Capacity constraint",
    "Technology obsolescence",
    "Operational resilience gap",
)


def _pick_zone_subzone(zone_maps):
    """Return (zone_name, sub_zone_name, sub_zone_id, capability_id)."""
    sub_zone_name, sub_zone_id = random.choice(zone_maps["sub_zones"])
    capability_id = random.choice(zone_maps["capabilities_by_sub"][sub_zone_id])
    zone_name = zone_maps["sub_to_zone"][sub_zone_id]
    return zone_name, sub_zone_name, sub_zone_id, capability_id


def _random_budget_amounts(category):
    """Return dict of year capex/opex per Excel rules."""
    years = (2026, 2027, 2028, 2029)
    span = random.randint(1, 3)
    start_idx = random.randint(0, len(years) - span)
    active_years = years[start_idx : start_idx + span]
    amounts = {}
    for year in years:
        if year in active_years:
            total = random.randint(0, 30) * 100_000
            if category == "Licenses/Support":
                amounts[f"capex_{year}"] = 0.0
                amounts[f"opex_{year}"] = float(total)
            elif category == "Project":
                capex = round(total * 0.8 / 100_000) * 100_000
                opex = total - capex
                amounts[f"capex_{year}"] = float(capex)
                amounts[f"opex_{year}"] = float(opex)
            else:
                split = random.choice([True, False])
                if split:
                    amounts[f"capex_{year}"] = float(total // 2)
                    amounts[f"opex_{year}"] = float(total - total // 2)
                else:
                    amounts[f"capex_{year}"] = float(total)
                    amounts[f"opex_{year}"] = 0.0
        else:
            amounts[f"capex_{year}"] = 0.0
            amounts[f"opex_{year}"] = 0.0
    return amounts


def generate_budgets(zone_maps, count=50):
    rows = []
    for i in range(1, count + 1):
        line_id = f"Budget-{i:04d}"
        budget_id = f"{random.randint(1000000000, 9999999999)}"
        category = random.choice(BUDGET_CATEGORIES)
        zone_name, sub_zone_name, sub_zone_id, _ = _pick_zone_subzone(zone_maps)
        amounts = _random_budget_amounts(category)
        title = f"{category} — {sub_zone_name} initiative {i}"
        rows.append(
            {
                "line_id": line_id,
                "budget_id": budget_id,
                "title": title,
                "description": f"Budget line covering {category.lower()} spend for {sub_zone_name}.",
                "status": random.choice(BUDGET_STATUSES),
                "category": category,
                "spend_type": random.choice(SPEND_TYPES),
                "sub_zone_id": sub_zone_id,
                "contact": random.choice(RENAISSANCE_ARTISTS),
                **amounts,
            }
        )
    return rows


def generate_projects(budgets, zone_maps, count=50):
    rows = []
    for i in range(1, count + 1):
        budget = budgets[i - 1]
        rows.append(
            {
                "line_id": f"Project-{i:04d}",
                "budget_id": budget["budget_id"],
                "title": budget["title"],
                "description": budget["description"],
                "sub_zone_id": budget["sub_zone_id"],
                "priority_2027": random.choice(["P1", "P2", "P3", "P4", ""]),
                "outcomes": "• Improved service reliability\n• Reduced manual effort\n• Better compliance posture",
                "compliance_impact": random.choice(
                    ["None", "GDPR review required", "SOX controls updated", "PCI scope change"]
                ),
                "delivery_approach": "• Agile delivery with fortnightly releases\n• Cross-functional squad model\n• Early stakeholder engagement",
                "delivery_constraints": "• Limited SME availability in Q3\n• Fixed regulatory deadline in December",
                "delivery_assumptions": "• Vendor support remains available\n• Cloud capacity approved before build",
                "out_of_scope": "• Legacy data archival\n• End-user training beyond pilot group",
            }
        )
    return rows


def generate_risks(zone_maps, count=50):
    rows = []
    for i in range(1, count + 1):
        status = random.choice(RISK_STATUSES)
        created = date(2024, 1, 1) + timedelta(days=random.randint(0, 500))
        closed = None
        if status == "Closed":
            closed = created + timedelta(days=random.randint(31, 180))
        _, _, sub_zone_id, _ = _pick_zone_subzone(zone_maps)
        rows.append(
            {
                "id": f"RISK-{i:04d}",
                "sub_zone_id": sub_zone_id,
                "risk_response": random.choice(RISK_RESPONSES),
                "status": status,
                "category": random.choice(RISK_CATEGORIES),
                "risk_score": random.randint(1, 10),
                "name": f"{random.choice(RISK_NAMES)} ({i})",
                "description": "Risk identified during portfolio review requiring tracked response.",
                "risk_owner": random.choice(CARTOON_CHARACTERS),
                "proximity_band": random.choice(PROXIMITY_BANDS),
                "current_likelihood": random.choice(LIKELIHOODS),
                "current_impact_band": random.choice(IMPACT_BANDS),
                "date_created": created.isoformat(),
                "date_closed": closed.isoformat() if closed else None,
            }
        )
    return rows


def _deployment_dates(state):
    today = date(2026, 7, 20)
    if state == "Not yet deployed":
        deploy = today + timedelta(days=random.randint(30, 400))
        decomm = deploy + timedelta(days=random.randint(365, 1095))
        return deploy.isoformat(), decomm.isoformat()
    if state == "Live":
        deploy = today - timedelta(days=random.randint(100, 1500))
        decomm = deploy + timedelta(days=random.randint(365, 1095))
        return deploy.isoformat(), decomm.isoformat()
    if state == "Awaiting Decommissioning":
        deploy = today - timedelta(days=random.randint(800, 2000))
        decomm = today + timedelta(days=random.randint(30, 300))
        return deploy.isoformat(), decomm.isoformat()
    deploy = today - timedelta(days=random.randint(1500, 3000))
    decomm = today - timedelta(days=random.randint(30, 400))
    if decomm <= deploy + timedelta(days=365):
        decomm = deploy + timedelta(days=400)
    return deploy.isoformat(), decomm.isoformat()


def generate_architecture(zone_maps, count=50):
    rows = []
    for i in range(1, count + 1):
        outlook = random.choice(ARCH_OUTLOOKS)
        state = random.choice(DEPLOYMENT_STATES)
        deploy, decomm = _deployment_dates(state)
        _, _, sub_zone_id, capability_id = _pick_zone_subzone(zone_maps)
        rows.append(
            {
                "id": f"ARCH-{i:04d}",
                "name": f"{random.choice(ARCH_NAMES)} {i}",
                "description": "Application component supporting core business capabilities.",
                "comments": random.choice(["", "Under review", "Pending security assessment", ""]),
                "sub_zone_id": sub_zone_id,
                "capability_id": capability_id,
                "architect": random.choice(ASTRONAUTS),
                "architecture_outlook": outlook,
                "deployment_state": state,
                "deployment_date": deploy,
                "decommission_date": decomm,
                "in_scope_of_esa": random.choice(["yes"] * 9 + ["no"]),
                "class_of_service": random.choice(CLASS_OF_SERVICE),
                "host_type": random.choice(HOST_TYPES),
                "replaced_by_arch_id": None,
                "support_partner_l1": f"L1 Partner {random.randint(1, 20)}",
                "support_partner_l2": f"L2 Partner {random.randint(1, 20)}",
                "support_partner_l3": f"L3 Partner {random.randint(1, 20)}",
                "vendor": f"Vendor {random.randint(1, 30)}",
            }
        )
    for i in range(12, count + 1, 7):
        replacement = rows[i - 1]
        target = rows[i - 8]
        if target["deployment_state"] in ("Awaiting Decommissioning", "Decommissioned"):
            target["replaced_by_arch_id"] = replacement["id"]
    return rows


def apply_architecture_replacements(conn, architecture):
    """Set replacement links after all architecture rows exist."""
    for item in architecture:
        if item.get("replaced_by_arch_id"):
            conn.execute(
                """
                UPDATE architecture_components
                SET replaced_by_arch_id = ?
                WHERE id = ?
                """,
                (item["replaced_by_arch_id"], item["id"]),
            )


def generate_run_contracts(budgets, zone_maps, count=50):
    rows = []
    for i in range(1, count + 1):
        budget = budgets[i - 1]
        start = date(2024, 1, 1) + timedelta(days=random.randint(0, 900))
        years = random.choice([1, 2, 3])
        end = start + timedelta(days=365 * years)
        po_renewal = start + timedelta(days=365)
        _, _, sub_zone_id, _ = _pick_zone_subzone(zone_maps)
        status = random.choice(CONTRACT_STATUSES)
        rows.append(
            {
                "fin_id": f"Finance-{i:04d}",
                "service_type": random.choice(SERVICE_TYPES),
                "linked_budget_id": budget["budget_id"],
                "vendor_name": f"Esoteric Vendor {random.randint(1, 40)}",
                "manufacturer": f"Esoteric Manufacturer {random.randint(1, 40)}",
                "contract_name": f"Service contract {i}",
                "description": "Managed service covering operational support and maintenance.",
                "detailed_description": (
                    "Detailed scope includes incident management, patching, and reporting. "
                    "Service levels align with tier-2 operational requirements. "
                    "Escalation paths are defined for priority incidents. "
                    "Quarterly business reviews track performance and cost."
                ),
                "contract_start_date": start.isoformat(),
                "contract_end_date": end.isoformat(),
                "po_renewal_date": po_renewal.isoformat(),
                "contract_status": status,
                "vendor_manager": random.choice(FOOTBALL_PLAYERS),
                "operational_owner": random.choice(TENNIS_PLAYERS),
                "sub_zone_id": sub_zone_id,
            }
        )
    return rows


def generate_edges(projects, risks, architecture, budgets, run_contracts):
    """Build edges per the Excel edges tab guidance."""
    edges = []
    edge_num = 1

    def add(project_id, linked_type, linked_id, relationship):
        nonlocal edge_num
        edges.append(
            {
                "id": f"e{edge_num}",
                "project_id": project_id,
                "linked_type": linked_type,
                "linked_id": linked_id,
                "relationship": relationship,
            }
        )
        edge_num += 1

    active_contracts = [rc for rc in run_contracts if rc["contract_status"] == "Current"]

    for idx, project in enumerate(projects):
        pid = project["line_id"]

        risk_pool = risks[idx : idx + 3] if idx + 3 <= len(risks) else risks[idx % len(risks) :][:2]
        for risk in risk_pool:
            add(pid, "risk", risk["id"], random.choice(["resolves", "reduces"]))

        if idx % 2 == 0 and architecture:
            arch = architecture[idx % len(architecture)]
            rel = random.choice(["implemented", "modified", "version upgrade", "decommissioned"])
            add(pid, "architecture", arch["id"], rel)

        if idx % 3 == 0:
            other_budgets = [b for b in budgets if b["budget_id"] != project["budget_id"]]
            if other_budgets:
                target = random.choice(other_budgets)
                add(pid, "budget", target["line_id"], random.choice(["creates", "terminates"]))

        if idx % 4 == 0 and active_contracts:
            contract = active_contracts[idx % len(active_contracts)]
            add(pid, "run_contract", contract["fin_id"], "terminates")

    return edges


def generate_architecture_edges(architecture):
    """Inter-component relationships for the diagram view."""
    edges = []
    for i in range(min(30, len(architecture) - 1)):
        source = architecture[i]
        target = architecture[i + 1]
        rel = random.choice(["calls", "feeds", "reads", "publishes to", "replaces"])
        edges.append(
            {
                "id": f"ae{i + 1}",
                "source_id": source["id"],
                "target_id": target["id"],
                "relationship": rel,
            }
        )
    return edges


def build_zone_maps(conn):
    """Load sub-zone and capability lookups from an seeded connection."""
    sub_zones = [
        (row["name"], row["id"])
        for row in conn.execute("SELECT id, name FROM sub_zones ORDER BY id")
    ]
    sub_to_zone = {
        row["id"]: row["zone_name"]
        for row in conn.execute(
            """
            SELECT sz.id, z.name AS zone_name
            FROM sub_zones sz
            JOIN zones z ON z.id = sz.zone_id
            """
        )
    }
    capabilities_by_sub = {}
    for row in conn.execute("SELECT id, sub_zone_id FROM capabilities ORDER BY id"):
        capabilities_by_sub.setdefault(row["sub_zone_id"], []).append(row["id"])
    return {
        "sub_zones": sub_zones,
        "sub_to_zone": sub_to_zone,
        "capabilities_by_sub": capabilities_by_sub,
    }
