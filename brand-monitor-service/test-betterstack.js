// Quick diagnostic script to test Betterstack connection
import { Logtail } from '@logtail/node';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config({ path: '.env.local' });

const token = process.env.BETTERSTACK_SOURCE_TOKEN;

console.log('=== Betterstack Diagnostic ===');
console.log('Token:', token);
console.log('Token length:', token.length);

async function test() {
    try {
        console.log('\n1. Creating Logtail instance...');
        const logtail = new Logtail(token);
        console.log('✅ Logtail instance created');

        console.log('\n2. Sending test log...');
        await logtail.info('DIAGNOSTIC TEST - Direct Logtail call', {
            timestamp: new Date().toISOString(),
            test: true,
        });
        console.log('✅ Log method called');

        console.log('\n3. Flushing logs...');
        await logtail.flush();
        console.log('✅ Logs flushed to Betterstack');

        console.log('\n=== Test Complete ===');
        console.log('Check your Betterstack dashboard for: "DIAGNOSTIC TEST - Direct Logtail call"');

    } catch (error) {
        console.error('\n❌ Error:', error);
    }
}

test();
