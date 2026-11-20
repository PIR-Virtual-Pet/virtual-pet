const appDb = db.getSiblingDB("virtual_pet");

if (appDb.getUser("virtual_pet") === null) {
  appDb.createUser({
    user: "virtual_pet",
    pwd: "virtual_pet_password",
    roles: [{ role: "readWrite", db: "virtual_pet" }],
  });
}

const collections = appDb.getCollectionNames();
if (!collections.includes("pets")) {
  appDb.createCollection("pets");
}
if (!collections.includes("counters")) {
  appDb.createCollection("counters");
}

appDb.pets.createIndex({ name: 1 }, { name: "pets_name_idx" });

appDb.counters.updateOne(
  { _id: "pets" },
  { $setOnInsert: { seq: 0 } },
  { upsert: true }
);
