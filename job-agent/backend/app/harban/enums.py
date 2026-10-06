from __future__ import annotations

from enum import Enum


class ClientStage(str, Enum):
    DISCOVERED = "DISCOVERED"
    RESEARCHED = "RESEARCHED"
    QUALIFIED = "QUALIFIED"
    OUTREACH_READY = "OUTREACH_READY"
    CONTACTED = "CONTACTED"
    REPLIED = "REPLIED"
    DISCOVERY_CALL = "DISCOVERY_CALL"
    PROPOSAL = "PROPOSAL"
    NEGOTIATION = "NEGOTIATION"
    WON = "WON"
    LOST = "LOST"
    NO_FURTHER_CONTACT = "NO_FURTHER_CONTACT"


class OpportunityType(str, Enum):
    JOB = "JOB"
    CLIENT = "CLIENT"
    BOTH = "BOTH"
    NEITHER = "NEITHER"


class OutreachChannel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    REFERRAL = "referral"


class ServiceStatus(str, Enum):
    DELIVERED = "DELIVERED"
    PLANNED = "PLANNED"
    DISCUSSION = "DISCUSSION"


_ALLOWED_CLIENT_TRANSITIONS: dict[ClientStage, set[ClientStage]] = {
    ClientStage.DISCOVERED: {ClientStage.RESEARCHED, ClientStage.LOST, ClientStage.NO_FURTHER_CONTACT},
    ClientStage.RESEARCHED: {ClientStage.QUALIFIED, ClientStage.LOST, ClientStage.NO_FURTHER_CONTACT},
    ClientStage.QUALIFIED: {ClientStage.OUTREACH_READY, ClientStage.LOST, ClientStage.NO_FURTHER_CONTACT},
    ClientStage.OUTREACH_READY: {ClientStage.CONTACTED, ClientStage.LOST, ClientStage.NO_FURTHER_CONTACT},
    ClientStage.CONTACTED: {ClientStage.REPLIED, ClientStage.NO_FURTHER_CONTACT, ClientStage.LOST, ClientStage.CONTACTED},
    ClientStage.REPLIED: {ClientStage.DISCOVERY_CALL, ClientStage.LOST, ClientStage.NO_FURTHER_CONTACT, ClientStage.PROPOSAL},
    ClientStage.DISCOVERY_CALL: {ClientStage.PROPOSAL, ClientStage.LOST, ClientStage.NO_FURTHER_CONTACT},
    ClientStage.PROPOSAL: {ClientStage.NEGOTIATION, ClientStage.LOST, ClientStage.WON, ClientStage.NO_FURTHER_CONTACT},
    ClientStage.NEGOTIATION: {ClientStage.WON, ClientStage.LOST, ClientStage.NO_FURTHER_CONTACT},
    ClientStage.WON: set(),
    ClientStage.LOST: set(),
    ClientStage.NO_FURTHER_CONTACT: set(),
}


def is_valid_client_transition(from_stage: ClientStage, to_stage: ClientStage) -> bool:
    if from_stage == to_stage:
        return True
    return to_stage in _ALLOWED_CLIENT_TRANSITIONS.get(from_stage, set())
