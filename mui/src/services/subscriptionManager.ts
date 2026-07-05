import websocket from "./websocket";
import type { components } from '@/api/schema';

type Callback = (update: Record<string, unknown>) => void;
type WSControlMessage = components["schemas"]["WSControlMessage"];
export type SubscriptionTarget = WSControlMessage["target"];
export type SubscriptionParams = WSControlMessage["params"];

/**
 * This class is responsive for subscription system
 * 1. If totally new subscription is requested, service need to create it and add listener
 * 2. If existing subscription is requested, service need to just add listener (no subscription recreation)
 * 3. If all listeners of specific update are unsubscribed, service must unsubscribe it.
 */
class SubscriptionManager {
   // Mappings
   private keyToId: Record<string, string> = {};
   private idToCallbacks: Record<string, Set<Callback>> = {};
   private idToParams: Record<string, Record<string, unknown>> = {};

   constructor() {
      websocket.subscribeMessages(this.onUpdate.bind(this));
      // websocket.subscribeState(() => {
      //    const status = websocket.getState().connectionStatus;
      //    if (status === 'disconnected') {
      //       this.needReconnection = true;
      //    }

      //    if (status === 'connected' && this.needReconnection) {
      //       Object.keys(this.idToParams).forEach(id => {
      //          this._createSubscription(id, this.idToParams[id]!);
      //       })
      //       this.needReconnection = false;
      //    }
      // })
   }

   /**
    * This function routes updates from websocket to callbacks
    */
   private onUpdate(message: string): void {
      try {
         const update = JSON.parse(message);

         if (!update.type || typeof update.type !== 'string') return;
         if (!update.id || typeof update.id !== 'string') return;

         this.idToCallbacks[update.id]?.forEach(callback => callback(update));
      } catch (error) {
         console.error("[SubscriptionManager] Error occur while parsing an update, " + error);
      }
   }

   getKeyFromParams(obj: unknown): string {
      // Primitives and null
      if (obj === null || obj === undefined) {
         return JSON.stringify(obj);
      }
      
      if (typeof obj === 'string' || typeof obj === 'number' || typeof obj === 'boolean') {
         return JSON.stringify(obj);
      }
      
      // Arrays
      if (Array.isArray(obj)) {
         return '[' + obj.map(item => this.getKeyFromParams(item)).join(',') + ']';
      }
      
      // Objects
      if (typeof obj === 'object') {
         const record = obj as Record<string, unknown>;
         const sortedKeys = Object.keys(record).sort();
         const sortedObj: Record<string, unknown> = {};
         
         for (const key of sortedKeys) {
            sortedObj[key] = this.getKeyFromParams(record[key]);
         }
         
         return JSON.stringify(sortedObj);
      }
      
      // Fallback for other types
      return '';
   }

   /**
    * Subscribe to new WebSocket update
    * @param params subscription parameters
    * @param callback callback function (executed on new update)
    */
   subscribe(params: Record<string, unknown>, callback: Callback): void {
      const key = this.getKeyFromParams(params);

      // If subscription with this parameters is not exist
      if (this.keyToId[key] === undefined) {
         // Create a new subscrition
         const id = crypto.randomUUID();
         this._createSubscription(id, params);

         this.keyToId[key] = id;
         this.idToParams[id] = params;
         if (this.idToCallbacks[id] === undefined) {
            this.idToCallbacks[id] = new Set();
         }
      }

      const id = this.keyToId[key];

      // Set up a callback
      this.idToCallbacks[id]!.add(callback);
   }

   private _createSubscription(id: string, params: Record<string, unknown>) {
      const subscribePayload = {
         action: 'subscribe',
         id: id,
         channel_id: websocket.getState().channelId,
         ...params
      };
      websocket.send(JSON.stringify(subscribePayload));
   }

   private _deleteSubscription(id: string, params: Record<string, unknown>) {
      const unsubscribePayload = {
         action: 'unsubscribe',
         id: id,
         channel_id: websocket.getState().channelId,
         ...params
      };
      websocket.send(JSON.stringify(unsubscribePayload));
   }

   /**
    * Usubscribe from a webSocket update
    * @param params subscription parameters
    * @param callback callback function to remove from subscribers
    */
   unsubscribe(params: Record<string, unknown>, callback: Callback): void {
      const key = this.getKeyFromParams(params);
      const id = this.keyToId[key];

      if (!id || ! this.idToCallbacks[id]) return;

      this.idToCallbacks[id].delete(callback);

      // If no one listens this subscription
      if (this.idToCallbacks[id].size === 0) {
         // Delete it
         this._deleteSubscription(id, params);

         delete this.idToCallbacks[id];
         delete this.keyToId[key];
         delete this.idToParams[id];
      }
   }
}

export default new SubscriptionManager();