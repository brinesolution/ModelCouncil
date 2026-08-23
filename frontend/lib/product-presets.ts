export type ProductScenarioTone = "favorable" | "mixed" | "premium" | "stress_test";

export interface ProductPreset {
  id: string;
  name: string;
  category: string;
  price: number;
  billingCadence: "one_time" | "monthly" | "yearly";
  scenarioTone: ProductScenarioTone;
  scenarioLabel: string;
  summary: string;
  pitch: string;
}

export const PRODUCT_PRESETS: readonly ProductPreset[] = [
  {
    id: "aegishome-local-securecam",
    name: "AegisHome Local SecureCam",
    category: "Smart Home Security Camera",
    price: 8999,
    billingCadence: "one_time",
    scenarioTone: "favorable",
    scenarioLabel: "Privacy-forward hardware",
    summary: "A one-time-purchase indoor security camera built around local processing, transparent pricing, and explicit privacy controls.",
    pitch: "AegisHome Local SecureCam is an indoor smart-home security camera for renters, families, small offices, and people who want useful alerts without making cloud storage mandatory. The camera records 2K video, supports configurable motion zones, person and package detection, night vision, two-way audio, and automatic event clips. Core detection runs locally on-device, local processing is the default, and recordings can be stored on an encrypted microSD card or a user-managed NAS. There is no required subscription, no recurring fee for the core camera features, and no cloud upload is required for normal operation. Optional encrypted cloud backup can be enabled separately, but the product continues to work without a cloud subscription. The microphone can be disabled in software and with a physical privacy control, users can define privacy zones, and the product provides clear controls for deleting local and optional cloud recordings. AegisHome uses transparent pricing with no hidden fees, publishes a security-update policy, and includes a two-year warranty plus responsive customer support. The device is designed for indoor use and is not weatherproof, it does not claim to replace a monitored emergency service, and advanced face recognition is intentionally not included. Setup requires Wi-Fi, a companion app for initial configuration, and user-supplied storage if local recording beyond the included capacity is desired. The product is positioned as a durable, privacy-preserving security device rather than an unlimited surveillance platform, and its main trade-off is that customers who want long off-site retention must configure optional cloud backup or their own network storage.",
  },
  {
    id: "flashbeat-pro-earbuds",
    name: "FlashBeat Pro ANC Earbuds",
    category: "Consumer Audio Electronics",
    price: 7999,
    billingCadence: "one_time",
    scenarioTone: "mixed",
    scenarioLabel: "Mainstream hardware trade-offs",
    summary: "Premium wireless earbuds with strong everyday features but realistic battery, repairability, and app-dependence trade-offs.",
    pitch: "FlashBeat Pro ANC Earbuds are wireless in-ear headphones aimed at commuters, office users, students, and frequent callers who want active noise cancellation without moving into the highest luxury price tier. The earbuds offer adaptive ANC, transparency mode, multipoint Bluetooth, low-latency mode, beamforming microphones, touch controls, an equalizer, hearing-safety volume reminders, and approximately seven hours of playback with ANC enabled under typical conditions. The charging case adds several additional charges and supports USB-C fast charging. The product is positioned as well built and tested for daily commuting, and the manufacturer provides a one-year warranty with standard replacement support. An optional companion app unlocks firmware updates, EQ presets, control remapping, and a find-my-earbuds feature; basic playback, calls, ANC, and transparency still work without an account after initial pairing. The earbuds do not require a subscription and have no recurring fee. Important trade-offs are stated clearly: the battery is sealed and not designed for user replacement, individual replacement parts are limited after the warranty period, microphone performance can degrade in very windy environments, and multipoint behavior can vary between older laptops and phones. The app collects diagnostic and device information when analytics is enabled, but analytics can be disabled and the product does not depend on personalized advertising. This scenario is intentionally mixed rather than perfect: strong convenience and audio features are balanced against serviceability limits, finite battery life, optional app complexity, and the normal uncertainty of long-term battery degradation.",
  },
  {
    id: "ledgerwise-budget-ai",
    name: "LedgerWise Budget AI",
    category: "Personal Finance Software",
    price: 399,
    billingCadence: "monthly",
    scenarioTone: "mixed",
    scenarioLabel: "Recurring software with sensitive data",
    summary: "A budgeting subscription that trades automation and time savings against recurring cost, account setup, and financial-data privacy concerns.",
    pitch: "LedgerWise Budget AI is a personal-finance budgeting service for salaried workers, freelancers, couples, and households that want automatic transaction categorization, cash-flow planning, savings goals, bill reminders, and a clearer monthly view of discretionary spending. Users can connect supported bank accounts through a regulated account-aggregation partner or import statements manually. The service automates category cleanup, highlights unusual spending, creates personalized budget suggestions, tracks recurring bills, and generates weekly summaries designed to save time compared with maintaining a spreadsheet. The subscription costs ₹399 per month with transparent pricing, self-service cancellation, and no long commitment; customers can export their data before cancelling. LedgerWise requires an account because budgets, linked accounts, and preferences must persist between devices. Financial records are encrypted in transit and at rest, advertising use of transaction data is disabled by default, and users can disconnect linked institutions and request deletion of stored financial records. The company states that the product is a budgeting and planning tool, not investment, tax, lending, or legal advice, and it does not guarantee savings outcomes. Responsive customer support is available for connection failures and account-recovery issues. Trade-offs include a recurring monthly fee, setup complexity for users with many accounts, imperfect automatic categorization that sometimes needs manual correction, and the privacy sensitivity inherent in processing personal financial data. Manual CSV import is available for customers who prefer not to connect a live bank feed, but some automation features are reduced in that mode.",
  },
  {
    id: "robosweep-r8",
    name: "RoboSweep R8 Mapping Vacuum",
    category: "Home Appliance Robotics",
    price: 27999,
    billingCadence: "one_time",
    scenarioTone: "premium",
    scenarioLabel: "Premium durable appliance",
    summary: "A higher-priced robot vacuum with mapping, repair support, and local controls, balanced by maintenance and home-layout limitations.",
    pitch: "RoboSweep R8 Mapping Vacuum is a premium robot vacuum and mop designed for apartments and medium-sized homes where owners value routine cleaning automation and are willing to pay more for mapping, obstacle avoidance, and serviceability. The robot uses lidar mapping, room-level cleaning schedules, carpet detection, adjustable suction, a removable mop module, no-go zones, and an auto-empty dock with replaceable bags. It can save multiple floor maps and offers both app control and physical start, pause, and return-to-dock buttons. Mapping and scheduling continue to work on the local network after setup, while remote control outside the home requires an optional cloud connection. There is no required subscription and no recurring software fee. The product is marketed as durable and repairable relative to many sealed appliances: brushes, filters, wheels, batteries, and several wear components are sold as replacement parts, and the manufacturer provides a two-year warranty plus published maintenance guidance. The purchase price of ₹27,999 is deliberately premium, and ongoing consumables such as filters, brushes, and dock bags create additional ownership cost even though they are not a subscription. Limitations include weaker performance on very thick rugs, difficulty with loose cables and low furniture, periodic sensor cleaning, and the need to manually refill or clean the mop system. The product does not claim to replace deep manual cleaning and may require map correction after major furniture changes. This scenario tests whether useful automation, reliability, repairability, and convenience can offset a clearly premium one-time price for some households while remaining unattractive to consumers with low need, small spaces, or high price sensitivity.",
  },
  {
    id: "voltrush-x20-stress",
    name: "VoltRush X20 Power Bank",
    category: "Portable Power Bank",
    price: 2999,
    billingCadence: "one_time",
    scenarioTone: "stress_test",
    scenarioLabel: "Adversarial reliability stress test",
    summary: "A deliberately problematic hardware brief for checking whether reliability, safety, support, and exaggerated claims create a real skeptical segment.",
    pitch: "VoltRush X20 Power Bank is a deliberately problematic stress-test product brief rather than a recommended consumer product. It is sold as a 20,000 mAh fast-charging battery pack for phones, tablets, and some laptops at a one-time price of ₹2,999, with no subscription. The marketing promises guaranteed all-day laptop power and unusually fast charging across nearly every device, but the claims are not supported by clear independent validation. Customer-facing product notes describe unreliable measured capacity, inconsistent charging behavior, frequent connection drops on USB-C power delivery, excessive heat during high-output use, and occasional overheating. Battery certification information is vague, the enclosure is sealed, the battery is not repairable, and replacement parts are limited. Warranty exclusions are extensive, difficult returns are reported in the scenario, and slow customer support makes replacement or refund problems harder to resolve. The packaging emphasizes premium cells and advanced protection circuitry, but the stress-test brief specifically leaves certification evidence and long-term reliability uncertain. Capacity can fall well below the advertised figure under sustained high-output loads, and some older devices negotiate charging poorly. The product does not collect personal data and has no app, account, cloud service, or recurring fee, so privacy risk is low; the central objections are quality, safety, serviceability, support, exaggerated claims, and whether a relatively low purchase price should compensate for those risks. This preset exists to verify that ModelCouncil can produce meaningful criticism and negative opinion without using a forced negative quota when the supplied product evidence is genuinely adverse.",
  },
] as const;

export const DEFAULT_PRODUCT_PRESET_ID = PRODUCT_PRESETS[0].id;

export function getProductPreset(id: string): ProductPreset | undefined {
  return PRODUCT_PRESETS.find((preset) => preset.id === id);
}
